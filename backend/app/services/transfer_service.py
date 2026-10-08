"""调拨申请；跨仓须审批后过账。"""

from __future__ import annotations  # 启用延后求值注解，支持前向引用类型

from datetime import UTC, datetime  # 导入 UTC 时间，用于单号与提交/执行时间
from typing import Any  # 导入 Any，序列化结果用宽松字典

from sqlalchemy import and_, delete, exists, func, or_, select  # 导入组合条件、删除、存在性与查询构造
from sqlalchemy.orm import Session, aliased  # 导入会话，以及库位自连接别名

from backend.app.core.errors import AppError  # 导入业务异常
from backend.app.models import (  # 从 models 导入调拨相关实体
    ApprovalTask,  # 审批任务
    Product,  # 商品
    TransferItem,  # 调拨明细
    TransferOrder,  # 调拨单
    UserWarehouseScope,  # 用户仓库授权
    WarehouseLocation,  # 库位
)  # 结束 models 导入
from backend.app.services.user_service import account_name  # 按用户 ID 解析用户名
from backend.app.dependencies import ensure_warehouse_scope  # 校验用户是否有目标仓库权限
from backend.app.schemas.transfers import TransferUpsert  # 调拨创建/更新入参
from backend.app.services.inventory_service import (  # 从库存服务导入过账与幂等辅助
    ServiceResult,  # 统一服务返回（body + 状态码）
    execute_transfer_line,  # 执行单行调拨过账
    record_idempotent_response,  # 写入幂等响应缓存
    replay_result,  # 回放已成功的幂等结果
    require_idempotency_key,  # 校验幂等键必填
    write_audit,  # 写审计日志
)  # 结束 inventory_service 导入


def _item_contexts(  # 校验明细商品/库位，并收集仓库上下文
    db: Session,  # 数据库会话
    payload: TransferUpsert,  # 调拨入参
    *,  # 后续必须关键字传参
    user_id: int,  # 当前用户
    roles: set[str],  # 当前角色
) -> list[tuple[int, int, int, int, int, int]]:  # 返回 (商品, 源库位, 目标库位, 数量, 源仓, 目标仓)
    contexts: list[tuple[int, int, int, int, int, int]] = []  # 校验通过的明细上下文
    warehouse_ids: set[int] = set()  # 本单涉及的全部仓库
    for item in payload.items:  # 逐行校验明细
        product = db.get(Product, item.product_id)  # 读取商品
        source = db.get(WarehouseLocation, item.source_location_id)  # 读取源库位
        target = db.get(WarehouseLocation, item.target_location_id)  # 读取目标库位
        if product is None:  # 商品不存在
            raise AppError(  # 拒绝不存在的商品
                "PRODUCT_NOT_FOUND",  # 错误码
                "商品不存在",  # 提示
                404,  # HTTP 状态
                {"product_id": item.product_id},  # 附带商品 ID
            )  # 结束商品不存在异常
        if source is None:  # 源库位不存在
            raise AppError(  # 拒绝无效源库位
                "WAREHOUSE_LOCATION_NOT_FOUND",  # 错误码
                "源库位不存在",  # 提示
                404,  # HTTP 状态
                {"location_id": item.source_location_id},  # 附带来源库位 ID
            )  # 结束源库位异常
        if target is None:  # 目标库位不存在
            raise AppError(  # 拒绝无效目标库位
                "WAREHOUSE_LOCATION_NOT_FOUND",  # 错误码
                "目标库位不存在",  # 提示
                404,  # HTTP 状态
                {"location_id": item.target_location_id},  # 附带目标库位 ID
            )  # 结束目标库位异常
        warehouse_ids.add(source.warehouse_id)  # 收集源仓
        warehouse_ids.add(target.warehouse_id)  # 收集目标仓
        contexts.append(  # 追加一行上下文
            (  # 明细元组
                item.product_id,  # 商品
                item.source_location_id,  # 源库位
                item.target_location_id,  # 目标库位
                item.quantity,  # 调拨数量
                source.warehouse_id,  # 源仓
                target.warehouse_id,  # 目标仓
            )  # 结束明细元组
        )  # 结束 append
    ensure_warehouse_scope(db, user_id, roles, warehouse_ids)  # 源仓和目标仓都必须有权限
    if contexts:  # 有明细才判定同仓/跨仓
        _classify_scope(contexts)  # 混合同仓与跨仓会直接抛错
    return contexts  # 返回校验后的上下文


def _warehouse_ids_for_items(db: Session, items: list[TransferItem]) -> set[int]:  # 从已有明细还原涉及仓库
    warehouse_ids: set[int] = set()  # 仓库集合
    for item in items:  # 逐行看源/目标库位
        source = db.get(WarehouseLocation, item.source_location_id)  # 读取源库位
        target = db.get(WarehouseLocation, item.target_location_id)  # 读取目标库位
        if source is not None:  # 源库位仍存在
            warehouse_ids.add(source.warehouse_id)  # 加入源仓
        if target is not None:  # 目标库位仍存在
            warehouse_ids.add(target.warehouse_id)  # 加入目标仓
    return warehouse_ids  # 返回涉及仓库


def _granted_warehouse_ids(db: Session, user_id: int) -> set[int]:  # 查询用户已授权仓库
    return set(  # 转成集合便于 in/not_in
        db.scalars(  # 取仓库 ID 标量
            select(UserWarehouseScope.warehouse_id).where(  # 只要仓库列
                UserWarehouseScope.user_id == user_id  # 限定当前用户
            )  # 结束 where
        )  # 结束 scalars
    )  # 结束授权仓库集合


def _locked_order(db: Session, transfer_id: int) -> TransferOrder | None:  # 行锁调拨单，防止并发改状态
    return db.scalar(  # 取单条单据
        select(TransferOrder)  # 查询调拨单
        .where(TransferOrder.transfer_order_id == transfer_id)  # 按主键定位
        .with_for_update()  # 加行锁直到事务结束
    )  # 结束加锁查询


def _classify_scope(contexts: list[tuple[int, int, int, int, int, int]]) -> str:  # 判定整单是同仓还是跨仓
    scopes: set[str] = set()  # 收集出现过的范围类型
    for *_, source_wh, target_wh in contexts:  # 只取源仓/目标仓
        scopes.add("intra_warehouse" if source_wh == target_wh else "cross_warehouse")  # 同仓或跨仓
    if len(scopes) > 1:  # 一张单不能混两种范围
        raise AppError("TRANSFER_SCOPE_MIXED", "同一调拨单不能同时包含同仓和跨仓明细", 422)  # 避免审批路径混乱
    return next(iter(scopes)) if scopes else "intra_warehouse"  # 无明细时按同仓占位


def _classify_items(db: Session, items: list[TransferItem]) -> str:  # 已落库明细再判定范围
    contexts: list[tuple[int, int, int, int, int, int]] = []  # 还原成与创建时相同的上下文
    for item in items:  # 逐行补仓库 ID
        source = db.get(WarehouseLocation, item.source_location_id)  # 读取源库位
        target = db.get(WarehouseLocation, item.target_location_id)  # 读取目标库位
        if source is None or target is None:  # 库位已被删
            raise AppError("WAREHOUSE_LOCATION_NOT_FOUND", "库位不存在", 404)  # 无法判定范围
        contexts.append(  # 追加一行上下文
            (  # 明细元组
                item.product_id,  # 商品
                item.source_location_id,  # 源库位
                item.target_location_id,  # 目标库位
                item.quantity,  # 数量
                source.warehouse_id,  # 源仓
                target.warehouse_id,  # 目标仓
            )  # 结束明细元组
        )  # 结束 append
    return _classify_scope(contexts)  # 复用混仓校验


def _apply_order_read_scope(  # 给列表/计数查询套上仓库可见范围
    statement: Any,  # 原始 SQLAlchemy 语句
    *,  # 后续必须关键字传参
    user_id: int,  # 当前用户
    roles: set[str],  # 当前角色
    granted_warehouses: set[int],  # 已授权仓库
):  # 返回加了 where 的语句
    if "admin" in roles:  # 管理员看全部
        return statement  # 不加范围过滤

    has_items = exists(  # 单据是否已有明细
        select(1)  # exists 只需常量列
        .select_from(TransferItem)  # 从调拨明细判断
        .where(TransferItem.transfer_order_id == TransferOrder.transfer_order_id)  # 关联当前单据
    )  # 结束存在性子查询
    if not granted_warehouses:  # 用户没有任何仓库授权
        return statement.where(  # 只能看自己建的空单
            and_(TransferOrder.created_by == user_id, ~has_items)  # 自己创建且尚无明细
        )  # 结束无授权过滤

    source_loc = aliased(WarehouseLocation)  # 源库位别名，避免与目标库位自连接冲突
    target_loc = aliased(WarehouseLocation)  # 目标库位别名
    has_out_of_scope_items = exists(  # 是否存在越权明细
        select(1)  # exists 只需常量列
        .select_from(TransferItem)  # 从调拨明细出发
        .join(source_loc, source_loc.location_id == TransferItem.source_location_id)  # 连接源库位
        .join(target_loc, target_loc.location_id == TransferItem.target_location_id)  # 连接目标库位
        .where(  # 越权条件
            TransferItem.transfer_order_id == TransferOrder.transfer_order_id,  # 关联当前单据
            or_(  # 源仓或目标仓任一不在授权内即越权
                source_loc.warehouse_id.not_in(granted_warehouses),  # 源仓越权
                target_loc.warehouse_id.not_in(granted_warehouses),  # 目标仓越权
            ),  # 结束 or
        )  # 结束 where
    )  # 结束越权存在性子查询
    return statement.where(  # 可见：自己的空单，或明细全部在授权仓内
        or_(  # 两种可见情形
            and_(TransferOrder.created_by == user_id, ~has_items),  # 自己创建的空草稿
            and_(has_items, ~has_out_of_scope_items),  # 有明细且无越权行
        )  # 结束 or
    )  # 结束范围过滤


def _ensure_order_read_scope(  # 详情读取时再校验一次仓库范围
    db: Session,  # 数据库会话
    order: TransferOrder,  # 调拨单
    items: list[TransferItem],  # 已加载明细
    *,  # 后续必须关键字传参
    user_id: int,  # 当前用户
    roles: set[str],  # 当前角色
) -> None:  # 无返回，失败则抛错
    if "admin" in roles:  # 管理员放行
        return  # 不校验仓库
    if not items:  # 空单只能创建人看
        if order.created_by != user_id:  # 不是创建人
            raise AppError("WAREHOUSE_SCOPE_FORBIDDEN", "没有目标仓库的操作权限", 403)  # 禁止偷看他人空单
        return  # 创建人可看自己的空单
    ensure_warehouse_scope(db, user_id, roles, _warehouse_ids_for_items(db, items))  # 有明细则必须覆盖全部涉及仓


def _replace_items(  # 用新上下文整表替换调拨明细
    db: Session,  # 数据库会话
    order_id: int,  # 调拨单 ID
    contexts: list[tuple[int, int, int, int, int, int]],  # 新明细上下文
) -> None:  # 无返回
    db.execute(delete(TransferItem).where(TransferItem.transfer_order_id == order_id))  # 先删旧明细
    db.add_all(  # 再插入新明细
        [  # 明细实体列表
            TransferItem(  # 一行调拨明细
                transfer_order_id=order_id,  # 归属单据
                product_id=product_id,  # 商品
                source_location_id=source_location_id,  # 源库位
                target_location_id=target_location_id,  # 目标库位
                quantity=quantity,  # 数量
            )  # 结束明细构造
            for product_id, source_location_id, target_location_id, quantity, *_ in contexts  # 解包上下文，忽略仓 ID
        ]  # 结束明细列表
    )  # 结束批量插入


def _serialize_order(  # 把调拨单序列化为接口字典
    db: Session,  # 数据库会话
    order: TransferOrder,  # 调拨单
    *,  # 后续必须关键字传参
    include_items: bool = True,  # 列表页可省略明细以减负
) -> dict[str, Any]:  # 返回序列化结果
    body: dict[str, Any] = {  # 单据头
        "transfer_order_id": order.transfer_order_id,  # 主键
        "order_no": order.order_no,  # 单号
        "status": order.status,  # 状态
        "transfer_scope": order.transfer_scope,  # 同仓/跨仓
        "created_by": order.created_by,  # 创建人
        "submitted_by": order.submitted_by,  # 提交人
        "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,  # 提交时间
        "executed_by": order.executed_by,  # 执行人
        "executed_at": order.executed_at.isoformat() if order.executed_at else None,  # 执行时间
        "username": account_name(db, order.executed_by or order.submitted_by or order.created_by),  # 展示最近操作人用户名
        "note": order.note,  # 备注
        "created_at": order.created_at.isoformat() if order.created_at else None,  # 创建时间
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,  # 更新时间
    }  # 结束单据头
    if include_items:  # 详情需要明细和审批摘要
        items = list(  # 按明细 ID 稳定排序
            db.scalars(  # 取明细实体
                select(TransferItem)  # 查询调拨明细
                .where(TransferItem.transfer_order_id == order.transfer_order_id)  # 限定本单
                .order_by(TransferItem.transfer_item_id)  # 按插入顺序
            )  # 结束 scalars
        )  # 结束明细列表
        body["items"] = [  # 序列化明细
            {  # 一行明细
                "transfer_item_id": item.transfer_item_id,  # 明细主键
                "product_id": item.product_id,  # 商品
                "source_location_id": item.source_location_id,  # 源库位
                "target_location_id": item.target_location_id,  # 目标库位
                "quantity": item.quantity,  # 数量
            }  # 结束一行明细
            for item in items  # 遍历明细
        ]  # 结束明细数组
        approval = db.scalar(  # 取本单调拨审批任务
            select(ApprovalTask).where(  # 按业务类型+业务 ID 定位
                ApprovalTask.business_type == "transfer",  # 调拨审批
                ApprovalTask.business_id == order.transfer_order_id,  # 本单
            )  # 结束 where
        )  # 结束审批查询
        if approval is not None:  # 已提交过才会有审批任务
            body["approval_summary"] = {  # 附带审批摘要
                "approval_task_id": approval.approval_task_id,  # 审批主键
                "business_type": approval.business_type,  # 业务类型
                "business_id": approval.business_id,  # 业务单 ID
                "status": approval.status,  # 审批状态
                "requested_by": approval.requested_by,  # 申请人
                "requested_at": approval.requested_at.isoformat()  # 申请时间，有值才格式化
                if approval.requested_at  # 已提交才有申请时间
                else None,  # 否则为空
                "decided_by": approval.decided_by,  # 审批人
                "decided_at": approval.decided_at.isoformat()  # 审批时间，有值才格式化
                if approval.decided_at  # 已决策才有时间
                else None,  # 否则为空
                "comment": approval.comment,  # 审批意见
            }  # 结束审批摘要
        else:  # 尚未进入审批
            body["approval_summary"] = None  # 列表/详情统一给空摘要
    return body  # 返回序列化单据


def create_transfer(  # 创建调拨草稿
    db: Session,  # 数据库会话
    *,  # 后续必须关键字传参
    payload: TransferUpsert,  # 创建入参
    user_id: int,  # 创建人
    roles: set[str],  # 创建人角色
    key: str | None,  # 幂等键
    request_id: str = "api",  # 请求追踪 ID
) -> ServiceResult:  # 返回 body + HTTP 状态
    key = require_idempotency_key(key)  # 强制要求幂等键
    prior = replay_result(db, user_id, key)  # 回放已成功的创建结果
    if prior is not None:  # 命中幂等
        return prior  # 直接返回上次结果

    contexts = _item_contexts(db, payload, user_id=user_id, roles=roles)  # 校验明细并收集仓库
    date_part = datetime.now(UTC).strftime("%Y%m%d")  # 单号日期段
    order = TransferOrder(  # 先用临时单号落库，拿到自增 ID 后再正式编号
        order_no=f"TR-{date_part}-TEMP",  # 临时单号，避免唯一约束冲突
        status="draft",  # 新建即为草稿
        created_by=user_id,  # 创建人
        note=payload.note,  # 备注
    )  # 结束单据构造
    db.add(order)  # 加入会话
    db.flush()  # 刷盘拿到 transfer_order_id
    order.order_no = f"TR-{date_part}-{order.transfer_order_id:06d}"  # 用主键补齐正式单号
    _replace_items(db, order.transfer_order_id, contexts)  # 写入明细
    db.flush()  # 刷盘明细
    body = _serialize_order(db, order)  # 序列化创建结果
    record_idempotent_response(  # 缓存创建响应
        db,  # 当前会话
        user_id=user_id,  # 操作者
        key=key,  # 幂等键
        method="POST",  # 创建方法
        path="/api/v1/transfers",  # 创建路径
        body=body,  # 响应体
        status=201,  # 创建成功状态码
    )  # 结束幂等缓存
    write_audit(  # 写创建审计
        db,  # 当前会话
        user_id=user_id,  # 操作者
        action="transfer_create",  # 审计动作
        entity_type="transfer_order",  # 实体类型
        entity_id=order.transfer_order_id,  # 新单据 ID
        after=body,  # 创建后快照
        request_id=request_id,  # 请求追踪
    )  # 结束审计写入
    db.commit()  # 提交事务
    return ServiceResult(body, 201)  # 返回创建结果


def update_transfer(  # 更新草稿调拨单
    db: Session,  # 数据库会话
    *,  # 后续必须关键字传参
    transfer_id: int,  # 调拨单 ID
    payload: TransferUpsert,  # 更新入参
    user_id: int,  # 操作者
    roles: set[str],  # 操作者角色
    key: str | None,  # 幂等键
    request_id: str = "api",  # 请求追踪 ID
) -> ServiceResult:  # 返回 body + HTTP 状态
    key = require_idempotency_key(key)  # 强制要求幂等键
    prior = replay_result(db, user_id, key)  # 回放已成功的更新结果
    if prior is not None:  # 命中幂等
        return prior  # 直接返回上次结果

    order = _locked_order(db, transfer_id)  # 加锁读取单据
    if order is None:  # 单据不存在
        raise AppError("TRANSFER_NOT_FOUND", "调拨单不存在", 404)  # 返回 404
    before = _serialize_order(db, order)  # 更新前快照
    if order.status != "draft":  # 仅草稿可改
        raise AppError("TRANSFER_STATE_INVALID", "当前调拨单不可修改", 409)  # 已提交则拒绝
    if order.created_by != user_id and "admin" not in roles:  # 非管理员只能改自己的单
        raise AppError("TRANSFER_FORBIDDEN", "只能修改自己创建的调拨单", 403)  # 权限不足

    contexts = _item_contexts(db, payload, user_id=user_id, roles=roles)  # 重新校验明细
    order.note = payload.note  # 更新备注
    _replace_items(db, transfer_id, contexts)  # 整表替换明细
    db.flush()  # 刷盘变更
    body = _serialize_order(db, order)  # 序列化更新结果
    record_idempotent_response(  # 缓存更新响应
        db,  # 当前会话
        user_id=user_id,  # 操作者
        key=key,  # 幂等键
        method="PUT",  # 更新方法
        path=f"/api/v1/transfers/{transfer_id}",  # 更新路径
        body=body,  # 响应体
        status=200,  # 成功状态码
    )  # 结束幂等缓存
    write_audit(  # 写更新审计
        db,  # 当前会话
        user_id=user_id,  # 操作者
        action="transfer_update",  # 审计动作
        entity_type="transfer_order",  # 实体类型
        entity_id=transfer_id,  # 单据 ID
        before=before,  # 更新前
        after=body,  # 更新后
        request_id=request_id,  # 请求追踪
    )  # 结束审计写入
    db.commit()  # 提交事务
    return ServiceResult(body, 200)  # 返回更新结果


def submit_transfer(  # 提交调拨单进入审批
    db: Session,  # 数据库会话
    *,  # 后续必须关键字传参
    transfer_id: int,  # 调拨单 ID
    user_id: int,  # 提交人
    roles: set[str],  # 提交人角色
    key: str | None,  # 幂等键
    request_id: str = "api",  # 请求追踪 ID
) -> ServiceResult:  # 返回 body + HTTP 状态
    key = require_idempotency_key(key)  # 强制要求幂等键
    prior = replay_result(db, user_id, key)  # 回放已成功的提交结果
    if prior is not None:  # 命中幂等
        return prior  # 直接返回上次结果

    order = _locked_order(db, transfer_id)  # 加锁读取单据
    if order is None:  # 单据不存在
        raise AppError("TRANSFER_NOT_FOUND", "调拨单不存在", 404)  # 返回 404
    before = _serialize_order(db, order)  # 提交前快照
    items = list(  # 加载全部明细
        db.scalars(select(TransferItem).where(TransferItem.transfer_order_id == transfer_id))  # 按单据过滤明细
    )  # 结束明细列表
    if not items:  # 空单不能提交
        raise AppError("TRANSFER_ITEMS_REQUIRED", "调拨明细不能为空", 422)  # 缺少明细
    if order.status != "draft":  # 仅草稿可提交
        raise AppError("TRANSFER_STATE_INVALID", "当前调拨单不可提交", 409)  # 状态冲突
    if order.created_by != user_id and "admin" not in roles:  # 非管理员只能提交自己的单
        raise AppError("TRANSFER_FORBIDDEN", "只能提交自己创建的调拨单", 403)  # 权限不足
    ensure_warehouse_scope(db, user_id, roles, _warehouse_ids_for_items(db, items))  # 提交时再核一次仓库权限

    now = datetime.now(UTC)  # 提交时间
    scope = _classify_items(db, items)  # 落库范围类型，供后续审批/执行使用
    order.transfer_scope = scope  # 写入同仓/跨仓
    order.submitted_by = user_id  # 记录提交人
    order.submitted_at = now  # 记录提交时间
    order.status = "pending_approval"  # 进入待审批
    db.add(  # 创建审批任务
        ApprovalTask(  # 调拨审批
            business_type="transfer",  # 业务类型
            business_id=transfer_id,  # 业务单 ID
            status="pending",  # 待审
            requested_by=user_id,  # 申请人
            requested_at=now,  # 申请时间
        )  # 结束审批构造
    )  # 结束 add
    db.flush()  # 刷盘状态与审批任务
    body = _serialize_order(db, order)  # 序列化提交结果
    record_idempotent_response(  # 缓存提交响应
        db,  # 当前会话
        user_id=user_id,  # 操作者
        key=key,  # 幂等键
        method="POST",  # 提交方法
        path=f"/api/v1/transfers/{transfer_id}/submit",  # 提交路径
        body=body,  # 响应体
        status=200,  # 成功状态码
    )  # 结束幂等缓存
    write_audit(  # 写提交审计
        db,  # 当前会话
        user_id=user_id,  # 操作者
        action="transfer_submit",  # 审计动作
        entity_type="transfer_order",  # 实体类型
        entity_id=transfer_id,  # 单据 ID
        before=before,  # 提交前
        after=body,  # 提交后
        request_id=request_id,  # 请求追踪
    )  # 结束审计写入
    db.commit()  # 提交事务
    return ServiceResult(body, 200)  # 返回提交结果


def execute_transfer(  # 审批通过后执行调拨过账
    db: Session,  # 数据库会话
    *,  # 后续必须关键字传参
    transfer_id: int,  # 调拨单 ID
    user_id: int,  # 执行人
    roles: set[str],  # 执行人角色
    key: str | None,  # 幂等键
    request_id: str = "api",  # 请求追踪 ID
) -> ServiceResult:  # 返回 body + HTTP 状态
    key = require_idempotency_key(key)  # 强制要求幂等键
    prior = replay_result(db, user_id, key)  # 回放已成功的执行结果
    if prior is not None:  # 命中幂等
        return prior  # 直接返回上次结果

    order = _locked_order(db, transfer_id)  # 加锁读取单据
    if order is None:  # 单据不存在
        raise AppError("TRANSFER_NOT_FOUND", "调拨单不存在", 404)  # 返回 404
    before = _serialize_order(db, order)  # 执行前快照
    if order.status != "executable":  # 只有审批通过后的可执行状态才能过账
        raise AppError("TRANSFER_STATE_INVALID", "当前调拨单不可执行", 409)  # 状态冲突
    items = list(  # 加载全部明细
        db.scalars(select(TransferItem).where(TransferItem.transfer_order_id == transfer_id))  # 按单据过滤明细
    )  # 结束明细列表
    if not items:  # 空单不能过账
        raise AppError("TRANSFER_ITEMS_REQUIRED", "调拨明细不能为空", 422)  # 缺少明细
    ensure_warehouse_scope(db, user_id, roles, _warehouse_ids_for_items(db, items))  # 执行人也必须有仓权限

    for item in items:  # 逐行调用库存服务过账
        execute_transfer_line(  # 库存增减只允许走 inventory_service
            db,  # 当前会话
            product_id=item.product_id,  # 商品
            source_location_id=item.source_location_id,  # 源库位扣减
            target_location_id=item.target_location_id,  # 目标库位增加
            quantity=item.quantity,  # 调拨数量
            source_id=transfer_id,  # 来源单据
            item_id=item.transfer_item_id,  # 来源明细
            key=key,  # 幂等键传到库存层
            user_id=user_id,  # 执行人
        )  # 结束单行过账

    now = datetime.now(UTC)  # 执行完成时间
    order.status = "completed"  # 单据完成
    order.executed_by = user_id  # 记录执行人
    order.executed_at = now  # 记录执行时间
    db.flush()  # 刷盘完成状态
    body = _serialize_order(db, order)  # 序列化执行结果
    record_idempotent_response(  # 缓存执行响应
        db,  # 当前会话
        user_id=user_id,  # 操作者
        key=key,  # 幂等键
        method="POST",  # 执行方法
        path=f"/api/v1/transfers/{transfer_id}/execute",  # 执行路径
        body=body,  # 响应体
        status=200,  # 成功状态码
    )  # 结束幂等缓存
    write_audit(  # 写执行审计
        db,  # 当前会话
        user_id=user_id,  # 操作者
        action="transfer_execute",  # 审计动作
        entity_type="transfer_order",  # 实体类型
        entity_id=transfer_id,  # 单据 ID
        before=before,  # 执行前
        after=body,  # 执行后
        request_id=request_id,  # 请求追踪
    )  # 结束审计写入
    db.commit()  # 提交事务
    return ServiceResult(body, 200)  # 返回执行结果


def mark_transfer_approved(db: Session, transfer_id: int) -> TransferOrder:  # 审批同意后把单据标为可执行
    order = _locked_order(db, transfer_id)  # 加锁读取单据
    if order is None:  # 单据不存在
        raise AppError("TRANSFER_NOT_FOUND", "调拨单不存在", 404)  # 返回 404
    if order.status != "pending_approval":  # 只有待审可同意
        raise AppError("TRANSFER_STATE_INVALID", "当前调拨单不可审批", 409)  # 状态冲突
    order.status = "executable"  # 同意后等待执行过账，不立刻改库存
    db.flush()  # 刷盘状态
    return order  # 返回已更新单据


def mark_transfer_rejected(db: Session, transfer_id: int) -> TransferOrder:  # 审批驳回后把单据标为驳回
    order = _locked_order(db, transfer_id)  # 加锁读取单据
    if order is None:  # 单据不存在
        raise AppError("TRANSFER_NOT_FOUND", "调拨单不存在", 404)  # 返回 404
    if order.status != "pending_approval":  # 只有待审可驳回
        raise AppError("TRANSFER_STATE_INVALID", "当前调拨单不可驳回", 409)  # 状态冲突
    order.status = "rejected"  # 驳回后不可执行
    db.flush()  # 刷盘状态
    return order  # 返回已更新单据


def list_transfers(  # 分页列出当前用户可见的调拨单
    db: Session,  # 数据库会话
    *,  # 后续必须关键字传参
    user_id: int,  # 当前用户
    roles: set[str],  # 当前角色
    page: int = 1,  # 页码，从 1 开始
    page_size: int = 20,  # 每页条数
    status: str | None = None,  # 可选状态，支持逗号分隔多选
    order_no: str | None = None,  # 可选单号模糊搜索
) -> dict[str, Any]:  # 返回分页列表
    statement = select(TransferOrder).order_by(TransferOrder.transfer_order_id.desc())  # 新单在前
    count_statement = select(func.count()).select_from(TransferOrder)  # 同步的计数查询
    if status:  # 有状态过滤
        statuses = [item.strip() for item in status.split(",") if item.strip()]  # 拆成多状态并去掉空段
        if len(statuses) == 1:  # 单状态用等号，便于走索引
            statement = statement.where(TransferOrder.status == statuses[0])  # 列表按精确状态过滤
            count_statement = count_statement.where(TransferOrder.status == statuses[0])  # 计数同样过滤
        elif statuses:  # 多状态用 IN
            statement = statement.where(TransferOrder.status.in_(statuses))  # 列表按状态集合过滤
            count_statement = count_statement.where(TransferOrder.status.in_(statuses))  # 计数同样过滤
    if order_no:  # 单号模糊搜索
        statement = statement.where(TransferOrder.order_no.ilike(f"%{order_no}%"))  # 忽略大小写包含
        count_statement = count_statement.where(TransferOrder.order_no.ilike(f"%{order_no}%"))  # 计数同样过滤

    granted_warehouses = _granted_warehouse_ids(db, user_id)  # 当前用户授权仓
    statement = _apply_order_read_scope(  # 给列表套仓库范围
        statement,  # 列表查询
        user_id=user_id,  # 当前用户
        roles=roles,  # 当前角色
        granted_warehouses=granted_warehouses,  # 授权仓
    )  # 结束列表范围
    count_statement = _apply_order_read_scope(  # 给计数套同样范围，避免总数对不上
        count_statement,  # 计数查询
        user_id=user_id,  # 当前用户
        roles=roles,  # 当前角色
        granted_warehouses=granted_warehouses,  # 授权仓
    )  # 结束计数范围

    total = int(db.scalar(count_statement) or 0)  # 范围内总条数
    rows = list(  # 本页单据
        db.scalars(statement.limit(page_size).offset((page - 1) * page_size))  # 按页切片
    )  # 结束本页列表
    return {  # 分页响应
        "items": [_serialize_order(db, row, include_items=False) for row in rows],  # 列表不带明细
        "total": total,  # 总条数
        "page": page,  # 当前页
        "page_size": page_size,  # 每页大小
    }  # 结束列表响应


def get_transfer(  # 读取调拨单详情
    db: Session,  # 数据库会话
    transfer_id: int,  # 调拨单 ID
    *,  # 后续必须关键字传参
    user_id: int,  # 当前用户
    roles: set[str],  # 当前角色
) -> dict[str, Any]:  # 返回序列化单据
    order = db.get(TransferOrder, transfer_id)  # 按主键读取单据
    if order is None:  # 单据不存在
        raise AppError("TRANSFER_NOT_FOUND", "调拨单不存在", 404)  # 返回 404
    items = list(  # 加载明细供范围校验
        db.scalars(select(TransferItem).where(TransferItem.transfer_order_id == transfer_id))  # 按单据过滤明细
    )  # 结束明细列表
    _ensure_order_read_scope(db, order, items, user_id=user_id, roles=roles)  # 详情也必须过仓库范围
    return _serialize_order(db, order)  # 返回含明细的详情
