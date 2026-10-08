"""盘点/调拨审批；创建人不能审自己的单。"""

from __future__ import annotations  # 启用延后求值注解，支持前向引用类型

from datetime import UTC, datetime  # 导入 UTC 时间，用于审批落账时间
from typing import Any  # 导入 Any，序列化结果用宽松字典

from sqlalchemy import func, select  # 导入聚合与查询构造
from sqlalchemy.orm import Session  # 导入 ORM 会话类型

from backend.app.core.errors import AppError  # 导入业务异常
from backend.app.models import (  # 从 models 导入审批及相关单据
    ApprovalTask,  # 审批任务
    StockCountItem,  # 盘点明细
    StockCountOrder,  # 盘点单
    TransferItem,  # 调拨明细
    TransferOrder,  # 调拨单
    WarehouseLocation,  # 库位，用于还原涉及仓库
)  # 结束 models 导入
from backend.app.dependencies import ensure_warehouse_scope  # 校验用户是否有目标仓库权限
from backend.app.schemas.approvals import ApprovalDecision  # 审批意见入参
from backend.app.services.inventory_service import (  # 从库存服务导入幂等与审计辅助
    ServiceResult,  # 统一服务返回（body + 状态码）
    record_idempotent_response,  # 写入幂等响应缓存
    replay_result,  # 回放已成功的幂等结果
    require_idempotency_key,  # 校验幂等键必填
    write_audit,  # 写审计日志
)  # 结束 inventory_service 导入
from backend.app.services.stock_count_service import approve_stock_count, reject_stock_count  # 盘点同意/驳回过账
from backend.app.services.transfer_service import mark_transfer_approved, mark_transfer_rejected  # 调拨同意/驳回改状态


def _iso(value: datetime | None) -> str | None:  # 把 datetime 转成 ISO 字符串
    return value.isoformat() if value else None  # 空值保持 None，避免前端收到无效时间


def _locked_task(db: Session, approval_id: int) -> ApprovalTask | None:  # 行锁审批任务，防止并发双审
    return db.scalar(  # 取单条任务
        select(ApprovalTask)  # 查询审批任务
        .where(ApprovalTask.approval_task_id == approval_id)  # 按主键定位
        .with_for_update()  # 加行锁直到事务结束
    )  # 结束加锁查询


def _business_order(db: Session, task: ApprovalTask):  # 按业务类型取对应单据
    if task.business_type == "stock_count":  # 盘点审批
        return db.get(StockCountOrder, task.business_id)  # 读取盘点单
    if task.business_type == "transfer":  # 调拨审批
        return db.get(TransferOrder, task.business_id)  # 读取调拨单
    raise AppError("APPROVAL_BUSINESS_UNSUPPORTED", "不支持的审批业务类型", 422)  # 未知类型直接拒绝


def _involved_warehouse_ids(db: Session, task: ApprovalTask) -> set[int]:  # 收集审批单涉及的仓库
    if task.business_type == "stock_count":  # 盘点：明细库位所在仓
        location_ids = list(  # 盘点明细上的库位
            db.scalars(  # 取库位 ID
                select(StockCountItem.location_id).where(  # 只要库位列
                    StockCountItem.stock_count_order_id == task.business_id  # 限定本盘点单
                )  # 结束 where
            )  # 结束 scalars
        )  # 结束库位 ID 列表
        if not location_ids:  # 无明细则无仓库约束
            return set()  # 空集合表示不按仓过滤
        return set(  # 库位映射到仓库并去重
            db.scalars(  # 取仓库 ID
                select(WarehouseLocation.warehouse_id).where(  # 只要仓库列
                    WarehouseLocation.location_id.in_(location_ids)  # 命中上述库位
                )  # 结束 where
            )  # 结束 scalars
        )  # 结束盘点仓库集合
    source_ids = list(  # 调拨来源库位
        db.scalars(  # 取来源库位 ID
            select(TransferItem.source_location_id).where(  # 源库位列
                TransferItem.transfer_order_id == task.business_id  # 限定本调拨单
            )  # 结束 where
        )  # 结束 scalars
    )  # 结束来源库位列表
    target_ids = list(  # 调拨目标库位
        db.scalars(  # 取目标库位 ID
            select(TransferItem.target_location_id).where(  # 目标库位列
                TransferItem.transfer_order_id == task.business_id  # 限定本调拨单
            )  # 结束 where
        )  # 结束 scalars
    )  # 结束目标库位列表
    location_ids = set(source_ids) | set(target_ids)  # 源仓+目标仓都要有权限
    if not location_ids:  # 无明细则无仓库约束
        return set()  # 空集合表示不按仓过滤
    return set(  # 库位映射到仓库并去重
        db.scalars(  # 取仓库 ID
            select(WarehouseLocation.warehouse_id).where(  # 只要仓库列
                WarehouseLocation.location_id.in_(location_ids)  # 命中源/目标库位
            )  # 结束 where
        )  # 结束 scalars
    )  # 结束调拨仓库集合


def _business_summary(db: Session, task: ApprovalTask) -> dict[str, Any] | None:  # 给列表页拼单据摘要
    order = _business_order(db, task)  # 读取对应业务单
    if order is None:  # 单据已被删或找不到
        return None  # 无摘要
    if task.business_type == "stock_count":  # 盘点摘要：统计明细行数
        item_count = int(  # 盘点明细条数
            db.scalar(  # 聚合计数
                select(func.count()).select_from(StockCountItem).where(  # 从盘点明细计数
                    StockCountItem.stock_count_order_id == order.stock_count_order_id  # 限定本单
                )  # 结束 where
            )  # 结束 scalar
            or 0  # 空结果当 0
        )  # 结束盘点明细计数
    else:  # 其余视为调拨
        item_count = int(  # 调拨明细条数
            db.scalar(  # 聚合计数
                select(func.count()).select_from(TransferItem).where(  # 从调拨明细计数
                    TransferItem.transfer_order_id == order.transfer_order_id  # 限定本单
                )  # 结束 where
            )  # 结束 scalar
            or 0  # 空结果当 0
        )  # 结束调拨明细计数
    return {  # 列表展示用摘要
        "business_type": task.business_type,  # 业务类型
        "order_no": order.order_no,  # 单号
        "status": order.status,  # 单据当前状态
        "requested_by": task.requested_by,  # 提交人
        "requested_at": _iso(task.requested_at),  # 提交时间
        "item_count": item_count,  # 明细行数
    }  # 结束摘要


def _serialize_task(db: Session, task: ApprovalTask) -> dict[str, Any]:  # 把审批任务序列化为接口字典
    summary = _business_summary(db, task)  # 附带业务摘要
    order = _business_order(db, task)  # 再取一次单据状态
    return {  # 组装审批详情
        "approval_task_id": task.approval_task_id,  # 审批主键
        "business_type": task.business_type,  # 业务类型
        "business_id": task.business_id,  # 业务单 ID
        "status": task.status,  # 审批状态
        "requested_by": task.requested_by,  # 申请人
        "requested_at": _iso(task.requested_at),  # 申请时间
        "decided_by": task.decided_by,  # 审批人
        "decided_at": _iso(task.decided_at),  # 审批时间
        "comment": task.comment,  # 审批意见
        "business_status": order.status if order is not None else None,  # 单据状态，单据缺失则为空
        "business_summary": summary,  # 列表/详情摘要
    }  # 结束任务序列化


def _authorize_decision(  # 审批前权限与状态校验
    db: Session,  # 数据库会话
    task: ApprovalTask,  # 当前审批任务
    user_id: int,  # 当前用户
    roles: set[str],  # 当前角色
) -> None:  # 无返回，失败则抛错
    if task.status != "pending":  # 非待审不能再处理
        raise AppError("APPROVAL_STATE_INVALID", "当前审批任务不可处理", 409)  # 状态冲突
    if task.requested_by == user_id and "admin" not in roles:  # 非管理员不能审自己的单
        raise AppError("APPROVAL_SELF_FORBIDDEN", "不能审批自己提交的单据", 403)  # 防自己批自己
    ensure_warehouse_scope(db, user_id, roles, _involved_warehouse_ids(db, task))  # 必须覆盖单据涉及的全部仓库


def list_approvals(  # 分页列出当前用户可见的审批任务
    db: Session,  # 数据库会话
    *,  # 后续必须关键字传参
    user_id: int,  # 当前用户
    roles: set[str],  # 当前角色
    page: int = 1,  # 页码，从 1 开始
    page_size: int = 20,  # 每页条数
    status: str | None = None,  # 可选审批状态过滤
    business_type: str | None = None,  # 可选业务类型过滤
    order_no: str | None = None,  # 可选关键字（单号/类型/状态中文）
) -> dict[str, Any]:  # 返回分页列表
    statement = select(ApprovalTask).order_by(ApprovalTask.approval_task_id.desc())  # 新任务在前
    if status:  # 按审批状态过滤
        statement = statement.where(ApprovalTask.status == status)  # 精确匹配状态
    if business_type:  # 按业务类型过滤
        statement = statement.where(ApprovalTask.business_type == business_type)  # 精确匹配类型
    rows = list(db.scalars(statement))  # 先取出候选任务，再在内存里做仓库范围过滤
    visible: list[ApprovalTask] = []  # 当前用户可见任务
    for task in rows:  # 逐条判断仓库范围
        warehouses = _involved_warehouse_ids(db, task)  # 本单涉及仓库
        if "admin" in roles or not warehouses:  # 管理员或无仓约束则可见
            visible.append(task)  # 加入可见列表
            continue  # 处理下一条
        try:  # 非管理员需覆盖全部涉及仓库
            ensure_warehouse_scope(db, user_id, roles, warehouses)  # 校验仓库授权
        except AppError:  # 任一仓库无权限
            continue  # 跳过该任务
        visible.append(task)  # 权限通过则可见
    if order_no:  # 关键字搜索：拼一段可检索文本再包含匹配
        needle = order_no.strip().lower()  # 去掉空白并转小写
        matched: list[ApprovalTask] = []  # 关键字命中结果
        for task in visible:  # 在可见范围内再搜
            summary = _business_summary(db, task)  # 取单号等摘要
            blob = " ".join(  # 把 ID、类型、单号、中文别名拼成搜索文本
                [  # 搜索字段集合
                    str(task.approval_task_id),  # 审批 ID
                    task.business_type or "",  # 业务类型编码
                    str(task.business_id),  # 业务单 ID
                    task.status or "",  # 审批状态编码
                    (summary or {}).get("order_no") or "",  # 业务单号
                    "盘点差异" if task.business_type == "stock_count" else "",  # 盘点中文别名
                    "调拨" if task.business_type == "transfer" else "",  # 调拨中文别名
                    "跨仓调拨" if task.business_type == "transfer" else "",  # 跨仓调拨别名
                    "待审批" if task.status == "pending" else "",  # 待审中文
                    "已同意" if task.status == "approved" else "",  # 已同意中文
                    "已驳回" if task.status == "rejected" else "",  # 已驳回中文
                ]  # 结束搜索字段
            ).lower()  # 统一小写再匹配
            if needle in blob:  # 包含关键字
                matched.append(task)  # 加入命中列表
        visible = matched  # 用搜索结果替换可见列表
    total = len(visible)  # 过滤后的总条数
    start = (page - 1) * page_size  # 计算切片起点
    page_rows = visible[start : start + page_size]  # 内存分页
    return {  # 分页响应
        "items": [_serialize_task(db, task) for task in page_rows],  # 本页任务
        "total": total,  # 总条数
        "page": page,  # 当前页
        "page_size": page_size,  # 每页大小
    }  # 结束列表响应


def get_approval(  # 读取单条审批详情
    db: Session,  # 数据库会话
    approval_id: int,  # 审批任务 ID
    *,  # 后续必须关键字传参
    user_id: int,  # 当前用户
    roles: set[str],  # 当前角色
) -> dict[str, Any]:  # 返回序列化任务
    task = db.get(ApprovalTask, approval_id)  # 按主键读取任务
    if task is None:  # 任务不存在
        raise AppError("APPROVAL_NOT_FOUND", "审批任务不存在", 404)  # 返回 404
    warehouses = _involved_warehouse_ids(db, task)  # 涉及仓库
    if warehouses:  # 有仓库约束才校验
        ensure_warehouse_scope(db, user_id, roles, warehouses)  # 无权限则 403
    return _serialize_task(db, task)  # 返回详情


def approve_task(  # 同意审批任务
    db: Session,  # 数据库会话
    *,  # 后续必须关键字传参
    approval_id: int,  # 审批任务 ID
    user_id: int,  # 审批人
    roles: set[str],  # 审批人角色
    payload: ApprovalDecision,  # 审批意见
    key: str | None,  # 幂等键
    request_id: str = "api",  # 请求追踪 ID
) -> ServiceResult:  # 返回 body + HTTP 状态
    key = require_idempotency_key(key)  # 强制要求幂等键
    prior = replay_result(db, user_id, key)  # 回放已成功的同意结果
    if prior is not None:  # 命中幂等
        return prior  # 直接返回上次结果

    task = _locked_task(db, approval_id)  # 加锁读取任务
    if task is None:  # 任务不存在
        raise AppError("APPROVAL_NOT_FOUND", "审批任务不存在", 404)  # 返回 404
    before = _serialize_task(db, task)  # 审批前快照
    _authorize_decision(db, task, user_id, roles)  # 校验状态、自审与仓库权限

    now = datetime.now(UTC)  # 审批落账时间
    if task.business_type == "stock_count":  # 盘点同意：走盘点过账
        approve_stock_count(  # 调用盘点审批过账，库存只允许走那边
            db,  # 当前会话，共用事务
            count_id=task.business_id,  # 盘点单 ID
            user_id=user_id,  # 审批人
            key=key,  # 同一幂等键
            request_id=request_id,  # 同一请求追踪
            path=f"/api/v1/approvals/{approval_id}/approve",  # 记到审批路径而非盘点路径
            commit=False,  # 外层统一提交
            record_idempotency=False,  # 外层统一记幂等
        )  # 结束盘点过账
    elif task.business_type == "transfer":  # 调拨同意：只改成可执行，不立刻扣账
        mark_transfer_approved(db, task.business_id)  # 单据变为 executable
        task.status = "approved"  # 任务标为已同意
        task.decided_by = user_id  # 记录审批人
        task.decided_at = now  # 记录审批时间
        task.comment = payload.comment  # 保存意见
        db.flush()  # 刷盘任务状态
    else:  # 未知业务类型
        raise AppError("APPROVAL_BUSINESS_UNSUPPORTED", "不支持的审批业务类型", 422)  # 拒绝处理

    task = db.get(ApprovalTask, approval_id)  # 盘点过账可能已改任务，重新读取
    if task is not None and task.status == "pending":  # 仍待审则在此补记同意
        task.status = "approved"  # 标为已同意
        task.decided_by = user_id  # 记录审批人
        task.decided_at = now  # 记录审批时间
        task.comment = payload.comment  # 保存意见
        db.flush()  # 刷盘补记结果

    body = _serialize_task(db, task) if task is not None else before  # 任务仍在则返回最新，否则用审批前快照
    record_idempotent_response(  # 缓存同意响应
        db,  # 当前会话
        user_id=user_id,  # 操作者
        key=key,  # 幂等键
        method="POST",  # 同意接口方法
        path=f"/api/v1/approvals/{approval_id}/approve",  # 同意路径
        body=body,  # 响应体
        status=200,  # 成功状态码
    )  # 结束幂等缓存
    write_audit(  # 写同意审计
        db,  # 当前会话
        user_id=user_id,  # 操作者
        action="approval_approve",  # 审计动作
        entity_type="approval_task",  # 实体类型
        entity_id=approval_id,  # 任务 ID
        before=before,  # 审批前
        after=body,  # 审批后
        request_id=request_id,  # 请求追踪
    )  # 结束审计写入
    db.commit()  # 提交整笔审批事务
    return ServiceResult(body, 200)  # 返回成功结果


def reject_task(  # 驳回审批任务
    db: Session,  # 数据库会话
    *,  # 后续必须关键字传参
    approval_id: int,  # 审批任务 ID
    user_id: int,  # 审批人
    roles: set[str],  # 审批人角色
    payload: ApprovalDecision,  # 审批意见（驳回必填）
    key: str | None,  # 幂等键
    request_id: str = "api",  # 请求追踪 ID
) -> ServiceResult:  # 返回 body + HTTP 状态
    if not payload.comment:  # 驳回必须写明原因
        raise AppError("APPROVAL_COMMENT_REQUIRED", "驳回时必须填写审批意见", 422)  # 缺少意见则拒绝
    key = require_idempotency_key(key)  # 强制要求幂等键
    prior = replay_result(db, user_id, key)  # 回放已成功的驳回结果
    if prior is not None:  # 命中幂等
        return prior  # 直接返回上次结果

    task = _locked_task(db, approval_id)  # 加锁读取任务
    if task is None:  # 任务不存在
        raise AppError("APPROVAL_NOT_FOUND", "审批任务不存在", 404)  # 返回 404
    before = _serialize_task(db, task)  # 驳回前快照
    _authorize_decision(db, task, user_id, roles)  # 校验状态、自审与仓库权限

    now = datetime.now(UTC)  # 驳回落账时间
    if task.business_type == "stock_count":  # 盘点驳回：解冻并改单据状态
        reject_stock_count(  # 调用盘点驳回，解冻库存
            db,  # 当前会话，共用事务
            count_id=task.business_id,  # 盘点单 ID
            user_id=user_id,  # 审批人
            key=key,  # 同一幂等键
            comment=payload.comment,  # 驳回意见写入盘点审批任务
            request_id=request_id,  # 同一请求追踪
            path=f"/api/v1/approvals/{approval_id}/reject",  # 记到审批路径
            commit=False,  # 外层统一提交
            record_idempotency=False,  # 外层统一记幂等
        )  # 结束盘点驳回
    elif task.business_type == "transfer":  # 调拨驳回：单据不可再执行
        mark_transfer_rejected(db, task.business_id)  # 单据变为 rejected
        task.status = "rejected"  # 任务标为已驳回
        task.decided_by = user_id  # 记录审批人
        task.decided_at = now  # 记录审批时间
        task.comment = payload.comment  # 保存驳回意见
        db.flush()  # 刷盘任务状态
    else:  # 未知业务类型
        raise AppError("APPROVAL_BUSINESS_UNSUPPORTED", "不支持的审批业务类型", 422)  # 拒绝处理

    task = db.get(ApprovalTask, approval_id)  # 盘点驳回可能已改任务，重新读取
    if task is not None and task.status == "pending":  # 仍待审则在此补记驳回
        task.status = "rejected"  # 标为已驳回
        task.decided_by = user_id  # 记录审批人
        task.decided_at = now  # 记录审批时间
        task.comment = payload.comment  # 保存驳回意见
        db.flush()  # 刷盘补记结果

    body = _serialize_task(db, task) if task is not None else before  # 任务仍在则返回最新，否则用驳回前快照
    record_idempotent_response(  # 缓存驳回响应
        db,  # 当前会话
        user_id=user_id,  # 操作者
        key=key,  # 幂等键
        method="POST",  # 驳回接口方法
        path=f"/api/v1/approvals/{approval_id}/reject",  # 驳回路径
        body=body,  # 响应体
        status=200,  # 成功状态码
    )  # 结束幂等缓存
    write_audit(  # 写驳回审计
        db,  # 当前会话
        user_id=user_id,  # 操作者
        action="approval_reject",  # 审计动作
        entity_type="approval_task",  # 实体类型
        entity_id=approval_id,  # 任务 ID
        before=before,  # 驳回前
        after=body,  # 驳回后
        request_id=request_id,  # 请求追踪
    )  # 结束审计写入
    db.commit()  # 提交整笔驳回事务
    return ServiceResult(body, 200)  # 返回成功结果
