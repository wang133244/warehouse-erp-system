"""盘点单与差异；过账须审批后走 inventory_service。"""

from __future__ import annotations  # 启用延后求值注解，支持前向引用类型

from datetime import UTC, datetime  # 导入 UTC 时间，用于单号与提交/完成时间
from typing import Any  # 导入 Any，序列化结果用宽松字典

from sqlalchemy import and_, delete, exists, func, or_, select  # 导入组合条件、删除、存在性与查询构造
from sqlalchemy.orm import Session  # 导入 ORM 会话类型

from backend.app.core.errors import AppError  # 导入业务异常
from backend.app.models import (  # 从 models 导入盘点相关实体
    ApprovalTask,  # 审批任务
    Product,  # 商品
    StockBalance,  # 库存余额，提交时锁定账面
    StockCountItem,  # 盘点明细
    StockCountOrder,  # 盘点单
    WarehouseLocation,  # 库位
    UserWarehouseScope,  # 用户仓库授权
)  # 结束 models 导入
from backend.app.dependencies import ensure_warehouse_scope  # 校验用户是否有目标仓库权限
from backend.app.schemas.stock_counts import StockCountUpsert  # 盘点创建/更新入参
from backend.app.services.inventory_service import (  # 从库存服务导入冻结、过账与幂等辅助
    ServiceResult,  # 统一服务返回（body + 状态码）
    apply_count_adjustment,  # 按实盘数量调整库存
    record_idempotent_response,  # 写入幂等响应缓存
    refresh_count_freeze,  # 按盘点差异刷新冻结量
    replay_result,  # 回放已成功的幂等结果
    require_idempotency_key,  # 校验幂等键必填
    write_audit,  # 写审计日志
)  # 结束 inventory_service 导入


def _item_contexts(  # 校验明细商品/库位，并收集仓库上下文
    db: Session,  # 数据库会话
    payload: StockCountUpsert,  # 盘点入参
    *,  # 后续必须关键字传参
    user_id: int,  # 当前用户
    roles: set[str],  # 当前角色
) -> list[tuple[int, int, int, int]]:  # 返回 (商品, 库位, 实盘数, 仓库)
    contexts: list[tuple[int, int, int, int]] = []  # 校验通过的明细上下文
    warehouse_ids: set[int] = set()  # 本单涉及的全部仓库
    for item in payload.items:  # 逐行校验明细
        product = db.get(Product, item.product_id)  # 读取商品
        location = db.get(WarehouseLocation, item.location_id)  # 读取库位
        if product is None:  # 商品不存在
            raise AppError(  # 拒绝不存在的商品
                "PRODUCT_NOT_FOUND",  # 错误码
                "商品不存在",  # 提示
                404,  # HTTP 状态
                {"product_id": item.product_id},  # 附带商品 ID
            )  # 结束商品不存在异常
        if not product.is_active:  # 商品已禁用
            raise AppError("PRODUCT_INACTIVE", "商品已禁用", 409, {"product_id": item.product_id})  # 禁用商品不可盘点
        if location is None:  # 库位不存在
            raise AppError(  # 拒绝无效库位
                "WAREHOUSE_LOCATION_NOT_FOUND",  # 错误码
                "库位不存在",  # 提示
                404,  # HTTP 状态
                {"location_id": item.location_id},  # 附带库位 ID
            )  # 结束库位异常
        if not location.is_active:  # 库位已禁用
            raise AppError("LOCATION_INACTIVE", "库位已禁用", 409, {"location_id": item.location_id})  # 禁用库位不可盘点
        warehouse_ids.add(location.warehouse_id)  # 收集涉及仓库
        contexts.append(  # 追加一行上下文
            (item.product_id, item.location_id, item.counted_quantity, location.warehouse_id)  # 商品、库位、实盘数、仓库
        )  # 结束 append
    ensure_warehouse_scope(db, user_id, roles, warehouse_ids)  # 明细涉及仓库都必须有权限
    return contexts  # 返回校验后的上下文


def _warehouse_ids_for_items(db: Session, items: list[StockCountItem]) -> set[int]:  # 从已有明细还原涉及仓库
    warehouse_ids: set[int] = set()  # 仓库集合
    for item in items:  # 逐行看库位
        location = db.get(WarehouseLocation, item.location_id)  # 读取库位
        if location is not None:  # 库位仍存在
            warehouse_ids.add(location.warehouse_id)  # 加入仓库
    return warehouse_ids  # 返回涉及仓库


def _granted_warehouse_ids(db: Session, user_id: int) -> set[int]:  # 查询用户已授权仓库
    return set(  # 转成集合便于 in/not_in
        db.scalars(  # 取仓库 ID 标量
            select(UserWarehouseScope.warehouse_id).where(  # 只要仓库列
                UserWarehouseScope.user_id == user_id  # 限定当前用户
            )  # 结束 where
        )  # 结束 scalars
    )  # 结束授权仓库集合


def _item_pairs(items: list[StockCountItem]) -> set[tuple[int, int]]:  # 抽出商品+库位对，供刷新冻结使用
    return {(item.product_id, item.location_id) for item in items}  # 去重后的盘点位置集合


def _locked_order(db: Session, count_id: int) -> StockCountOrder | None:  # 行锁盘点单，防止并发改状态
    return db.scalar(  # 取单条单据
        select(StockCountOrder)  # 查询盘点单
        .where(StockCountOrder.stock_count_order_id == count_id)  # 按主键定位
        .with_for_update()  # 加行锁直到事务结束
    )  # 结束加锁查询


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
        .select_from(StockCountItem)  # 从盘点明细判断
        .where(  # 关联当前单据
            StockCountItem.stock_count_order_id == StockCountOrder.stock_count_order_id  # 明细归属本单
        )  # 结束 where
    )  # 结束存在性子查询
    if not granted_warehouses:  # 用户没有任何仓库授权
        return statement.where(  # 只能看自己建的空单
            and_(StockCountOrder.created_by == user_id, ~has_items)  # 自己创建且尚无明细
        )  # 结束无授权过滤

    has_out_of_scope_items = exists(  # 是否存在越权明细
        select(1)  # exists 只需常量列
        .select_from(StockCountItem)  # 从盘点明细出发
        .join(  # 连接库位以取仓库
            WarehouseLocation,  # 库位表
            WarehouseLocation.location_id == StockCountItem.location_id,  # 按库位 ID 连接
        )  # 结束 join
        .where(  # 越权条件
            StockCountItem.stock_count_order_id == StockCountOrder.stock_count_order_id,  # 关联当前单据
            WarehouseLocation.warehouse_id.not_in(granted_warehouses),  # 库位所在仓不在授权内
        )  # 结束 where
    )  # 结束越权存在性子查询
    return statement.where(  # 可见：自己的空单，或明细全部在授权仓内
        or_(  # 两种可见情形
            and_(StockCountOrder.created_by == user_id, ~has_items),  # 自己创建的空草稿
            and_(has_items, ~has_out_of_scope_items),  # 有明细且无越权行
        )  # 结束 or
    )  # 结束范围过滤


def _ensure_order_read_scope(  # 详情读取时再校验一次仓库范围
    db: Session,  # 数据库会话
    order: StockCountOrder,  # 盘点单
    items: list[StockCountItem],  # 已加载明细
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


def _create_order(db: Session, *, user_id: int, note: str | None, status: str) -> StockCountOrder:  # 落库一张盘点单并生成正式单号
    date_part = datetime.now(UTC).strftime("%Y%m%d")  # 单号日期段
    order = StockCountOrder(  # 先用临时单号落库，拿到自增 ID 后再正式编号
        order_no=f"SC-{date_part}-TEMP",  # 临时单号，避免唯一约束冲突
        status=status,  # 有明细则 counting，否则 draft
        created_by=user_id,  # 创建人
        note=note,  # 备注
    )  # 结束单据构造
    db.add(order)  # 加入会话
    db.flush()  # 刷盘拿到 stock_count_order_id
    order.order_no = f"SC-{date_part}-{order.stock_count_order_id:06d}"  # 用主键补齐正式单号
    db.flush()  # 刷盘正式单号
    return order  # 返回新建单据


def _serialize_order(  # 把盘点单序列化为接口字典
    db: Session,  # 数据库会话
    order: StockCountOrder,  # 盘点单
    *,  # 后续必须关键字传参
    include_items: bool = True,  # 列表页可省略明细以减负
) -> dict[str, Any]:  # 返回序列化结果
    body: dict[str, Any] = {  # 单据头
        "stock_count_order_id": order.stock_count_order_id,  # 主键
        "order_no": order.order_no,  # 单号
        "status": order.status,  # 状态
        "created_by": order.created_by,  # 创建人
        "submitted_by": order.submitted_by,  # 提交人
        "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,  # 提交时间
        "completed_by": order.completed_by,  # 完成人
        "completed_at": order.completed_at.isoformat() if order.completed_at else None,  # 完成时间
        "note": order.note,  # 备注
        "created_at": order.created_at.isoformat() if order.created_at else None,  # 创建时间
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,  # 更新时间
    }  # 结束单据头
    if include_items:  # 详情需要明细和审批摘要
        items = list(  # 按明细 ID 稳定排序
            db.scalars(  # 取明细实体
                select(StockCountItem)  # 查询盘点明细
                .where(StockCountItem.stock_count_order_id == order.stock_count_order_id)  # 限定本单
                .order_by(StockCountItem.stock_count_item_id)  # 按插入顺序
            )  # 结束 scalars
        )  # 结束明细列表
        body["items"] = [  # 序列化明细
            {  # 一行明细
                "stock_count_item_id": item.stock_count_item_id,  # 明细主键
                "product_id": item.product_id,  # 商品
                "location_id": item.location_id,  # 库位
                "book_quantity": item.book_quantity,  # 账面数量
                "counted_quantity": item.counted_quantity,  # 实盘数量
                "variance_quantity": item.variance_quantity,  # 差异数量
            }  # 结束一行明细
            for item in items  # 遍历明细
        ]  # 结束明细数组
        approval = db.scalar(  # 取本单盘点审批任务
            select(ApprovalTask).where(  # 按业务类型+业务 ID 定位
                ApprovalTask.business_type == "stock_count",  # 盘点审批
                ApprovalTask.business_id == order.stock_count_order_id,  # 本单
            )  # 结束 where
        )  # 结束审批查询
        if approval is not None:  # 有差异提交后才会有审批任务
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
        else:  # 无差异或尚未进入审批
            body["approval_summary"] = None  # 列表/详情统一给空摘要
    return body  # 返回序列化单据


def create_stock_count(  # 创建盘点单
    db: Session,  # 数据库会话
    *,  # 后续必须关键字传参
    payload: StockCountUpsert,  # 创建入参
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
    status = "counting" if contexts else "draft"  # 有明细进入盘点中，否则空草稿
    order = _create_order(db, user_id=user_id, note=payload.note, status=status)  # 落库单据头
    db.add_all(  # 批量写入明细
        [  # 明细实体列表
            StockCountItem(  # 一行盘点明细
                stock_count_order_id=order.stock_count_order_id,  # 归属单据
                product_id=product_id,  # 商品
                location_id=location_id,  # 库位
                counted_quantity=counted_quantity,  # 实盘数量
            )  # 结束明细构造
            for product_id, location_id, counted_quantity, _warehouse_id in contexts  # 解包上下文，忽略仓 ID
        ]  # 结束明细列表
    )  # 结束批量插入
    db.flush()  # 刷盘明细
    body = _serialize_order(db, order)  # 序列化创建结果
    record_idempotent_response(  # 缓存创建响应
        db,  # 当前会话
        user_id=user_id,  # 操作者
        key=key,  # 幂等键
        method="POST",  # 创建方法
        path="/api/v1/stock-counts",  # 创建路径
        body=body,  # 响应体
        status=201,  # 创建成功状态码
    )  # 结束幂等缓存
    write_audit(  # 写创建审计
        db,  # 当前会话
        user_id=user_id,  # 操作者
        action="stock_count_create",  # 审计动作
        entity_type="stock_count_order",  # 实体类型
        entity_id=order.stock_count_order_id,  # 新单据 ID
        after=body,  # 创建后快照
        request_id=request_id,  # 请求追踪
    )  # 结束审计写入
    db.commit()  # 提交事务
    return ServiceResult(body, 201)  # 返回创建结果


def update_stock_count(  # 更新草稿/盘点中单据
    db: Session,  # 数据库会话
    *,  # 后续必须关键字传参
    count_id: int,  # 盘点单 ID
    payload: StockCountUpsert,  # 更新入参
    user_id: int,  # 操作者
    roles: set[str],  # 操作者角色
    key: str | None,  # 幂等键
    request_id: str = "api",  # 请求追踪 ID
) -> ServiceResult:  # 返回 body + HTTP 状态
    key = require_idempotency_key(key)  # 强制要求幂等键
    prior = replay_result(db, user_id, key)  # 回放已成功的更新结果
    if prior is not None:  # 命中幂等
        return prior  # 直接返回上次结果

    order = _locked_order(db, count_id)  # 加锁读取单据
    if order is None:  # 单据不存在
        raise AppError("STOCK_COUNT_NOT_FOUND", "盘点单不存在", 404)  # 返回 404
    before = _serialize_order(db, order)  # 更新前快照
    if order.status not in ("draft", "counting"):  # 仅草稿或盘点中可改
        raise AppError("STOCK_COUNT_STATE_INVALID", "当前盘点单不可编辑", 409)  # 已提交则拒绝
    if order.created_by != user_id and "admin" not in roles:  # 非管理员只能改自己的单
        raise AppError("STOCK_COUNT_FORBIDDEN", "只能编辑自己创建的盘点单", 403)  # 权限不足

    contexts = _item_contexts(db, payload, user_id=user_id, roles=roles)  # 重新校验明细
    db.execute(  # 先删旧明细再写入
        delete(StockCountItem).where(StockCountItem.stock_count_order_id == count_id)  # 整单替换明细
    )  # 结束删除
    db.add_all(  # 再插入新明细
        [  # 明细实体列表
            StockCountItem(  # 一行盘点明细
                stock_count_order_id=count_id,  # 归属单据
                product_id=product_id,  # 商品
                location_id=location_id,  # 库位
                counted_quantity=counted_quantity,  # 实盘数量
            )  # 结束明细构造
            for product_id, location_id, counted_quantity, _warehouse_id in contexts  # 解包上下文，忽略仓 ID
        ]  # 结束明细列表
    )  # 结束批量插入
    order.note = payload.note  # 更新备注
    order.status = "counting" if contexts else "draft"  # 有明细维持盘点中，清空则回草稿
    db.flush()  # 刷盘变更
    body = _serialize_order(db, order)  # 序列化更新结果
    record_idempotent_response(  # 缓存更新响应
        db,  # 当前会话
        user_id=user_id,  # 操作者
        key=key,  # 幂等键
        method="PUT",  # 更新方法
        path=f"/api/v1/stock-counts/{count_id}",  # 更新路径
        body=body,  # 响应体
        status=200,  # 成功状态码
    )  # 结束幂等缓存
    write_audit(  # 写更新审计
        db,  # 当前会话
        user_id=user_id,  # 操作者
        action="stock_count_update",  # 审计动作
        entity_type="stock_count_order",  # 实体类型
        entity_id=count_id,  # 单据 ID
        before=before,  # 更新前
        after=body,  # 更新后
        request_id=request_id,  # 请求追踪
    )  # 结束审计写入
    db.commit()  # 提交事务
    return ServiceResult(body, 200)  # 返回更新结果


def submit_stock_count(  # 提交盘点：锁账面、算差异，无差异直接完成
    db: Session,  # 数据库会话
    *,  # 后续必须关键字传参
    count_id: int,  # 盘点单 ID
    user_id: int,  # 提交人
    roles: set[str],  # 提交人角色
    key: str | None,  # 幂等键
    request_id: str = "api",  # 请求追踪 ID
) -> ServiceResult:  # 返回 body + HTTP 状态
    key = require_idempotency_key(key)  # 强制要求幂等键
    prior = replay_result(db, user_id, key)  # 回放已成功的提交结果
    if prior is not None:  # 命中幂等
        return prior  # 直接返回上次结果

    order = _locked_order(db, count_id)  # 加锁读取单据
    if order is None:  # 单据不存在
        raise AppError("STOCK_COUNT_NOT_FOUND", "盘点单不存在", 404)  # 返回 404
    before = _serialize_order(db, order)  # 提交前快照
    items = list(  # 加载全部明细
        db.scalars(  # 取明细实体
            select(StockCountItem).where(StockCountItem.stock_count_order_id == count_id)  # 按单据过滤明细
        )  # 结束 scalars
    )  # 结束明细列表
    if not items:  # 空单不能提交
        raise AppError("COUNT_ITEMS_REQUIRED", "盘点明细不能为空", 422)  # 缺少明细
    if order.status != "counting":  # 仅盘点中可提交
        raise AppError("STOCK_COUNT_STATE_INVALID", "当前盘点单不可提交", 409)  # 状态冲突
    if order.created_by != user_id and "admin" not in roles:  # 非管理员只能提交自己的单
        raise AppError("STOCK_COUNT_FORBIDDEN", "只能提交自己创建的盘点单", 403)  # 权限不足

    ensure_warehouse_scope(  # 提交时再核一次仓库权限
        db,  # 当前会话
        user_id,  # 提交人
        roles,  # 角色
        _warehouse_ids_for_items(db, items),  # 明细涉及仓库
    )  # 结束仓库校验
    now = datetime.now(UTC)  # 提交时间
    order.submitted_by = user_id  # 记录提交人
    order.submitted_at = now  # 记录提交时间

    variances: list[int] = []  # 收集各行差异，用于判断是否免审批
    for item in items:  # 逐行锁账面并计算差异
        balance = db.scalar(  # 锁对应库存余额
            select(StockBalance)  # 查询余额
            .where(  # 按商品+库位定位
                StockBalance.product_id == item.product_id,  # 同一商品
                StockBalance.location_id == item.location_id,  # 同一库位
            )  # 结束 where
            .with_for_update()  # 行锁，避免提交瞬间被别的过账改账面
        )  # 结束余额查询
        book_quantity = balance.quantity if balance is not None else 0  # 无余额行则账面为 0
        item.book_quantity = book_quantity  # 冻结提交时的账面
        item.variance_quantity = item.counted_quantity - book_quantity  # 实盘减账面得到差异
        variances.append(item.variance_quantity)  # 记录该行差异
    db.flush()  # 刷盘账面与差异

    if all(variance == 0 for variance in variances):  # 全部无差异则无需审批
        order.status = "completed"  # 直接完成
        order.completed_by = user_id  # 完成人即提交人
        order.completed_at = now  # 完成时间
    else:  # 存在差异则进入待审批
        order.status = "pending_approval"  # 等待审批后过账
        db.add(  # 创建审批任务
            ApprovalTask(  # 盘点差异审批
                business_type="stock_count",  # 业务类型
                business_id=count_id,  # 业务单 ID
                status="pending",  # 待审
                requested_by=user_id,  # 申请人
                requested_at=now,  # 申请时间
            )  # 结束审批构造
        )  # 结束 add
        db.flush()  # 刷盘待审状态与任务

    refresh_count_freeze(db, _item_pairs(items))  # 按差异刷新冻结，防止盘点期间被误出库
    body = _serialize_order(db, order)  # 序列化提交结果
    record_idempotent_response(  # 缓存提交响应
        db,  # 当前会话
        user_id=user_id,  # 操作者
        key=key,  # 幂等键
        method="POST",  # 提交方法
        path=f"/api/v1/stock-counts/{count_id}/submit",  # 提交路径
        body=body,  # 响应体
        status=200,  # 成功状态码
    )  # 结束幂等缓存
    write_audit(  # 写提交审计
        db,  # 当前会话
        user_id=user_id,  # 操作者
        action="stock_count_submit",  # 审计动作
        entity_type="stock_count_order",  # 实体类型
        entity_id=count_id,  # 单据 ID
        before=before,  # 提交前
        after=body,  # 提交后
        request_id=request_id,  # 请求追踪
    )  # 结束审计写入
    db.commit()  # 提交事务
    return ServiceResult(body, 200)  # 返回提交结果


def approve_stock_count(  # 审批同意后按实盘调整库存
    db: Session,  # 数据库会话
    *,  # 后续必须关键字传参
    count_id: int,  # 盘点单 ID
    user_id: int,  # 审批人
    key: str | None,  # 幂等键
    request_id: str = "api",  # 请求追踪 ID
    path: str = "/api/v1/stock-counts/{count_id}/approve",  # 幂等路径，审批入口可覆盖
    commit: bool = True,  # 审批服务调用时由外层提交
    record_idempotency: bool = True,  # 审批服务调用时由外层记幂等
) -> ServiceResult:  # 返回 body + HTTP 状态
    key = require_idempotency_key(key)  # 强制要求幂等键
    if record_idempotency:  # 直连盘点审批接口时才自己做幂等
        prior = replay_result(db, user_id, key)  # 回放已成功的同意结果
        if prior is not None:  # 命中幂等
            return prior  # 直接返回上次结果

    order = _locked_order(db, count_id)  # 加锁读取单据
    if order is None:  # 单据不存在
        raise AppError("STOCK_COUNT_NOT_FOUND", "盘点单不存在", 404)  # 返回 404
    before = _serialize_order(db, order)  # 审批前快照
    if order.status != "pending_approval":  # 只有待审可同意过账
        raise AppError("STOCK_COUNT_STATE_INVALID", "当前盘点单不可审批", 409)  # 状态冲突

    items = list(  # 加载全部明细
        db.scalars(  # 取明细实体
            select(StockCountItem).where(StockCountItem.stock_count_order_id == count_id)  # 按单据过滤明细
        )  # 结束 scalars
    )  # 结束明细列表
    execution_items: list[dict[str, int]] = []  # 审计用：提交账面 vs 执行时账面
    for item in items:  # 逐行过账
        balance = db.scalar(  # 再锁一次当前余额
            select(StockBalance)  # 查询余额
            .where(  # 按商品+库位定位
                StockBalance.product_id == item.product_id,  # 同一商品
                StockBalance.location_id == item.location_id,  # 同一库位
            )  # 结束 where
            .with_for_update()  # 行锁，保证调整基于最新账面
        )  # 结束余额查询
        execution_items.append(  # 记录执行快照，便于审计对账
            {  # 一行执行信息
                "stock_count_item_id": item.stock_count_item_id,  # 明细主键
                "product_id": item.product_id,  # 商品
                "location_id": item.location_id,  # 库位
                "submitted_book_quantity": item.book_quantity,  # 提交时账面
                "execution_book_quantity": balance.quantity if balance else 0,  # 执行时账面
                "target_quantity": item.counted_quantity,  # 调整目标即实盘数
            }  # 结束执行信息
        )  # 结束 append
        apply_count_adjustment(  # 库存调整只允许走 inventory_service
            db,  # 当前会话
            product_id=item.product_id,  # 商品
            location_id=item.location_id,  # 库位
            target_quantity=item.counted_quantity,  # 调到实盘数量
            source_id=count_id,  # 来源单据
            item_id=item.stock_count_item_id,  # 来源明细
            key=key,  # 幂等键传到库存层
            user_id=user_id,  # 审批人
            request_id=request_id,  # 请求追踪
        )  # 结束单行调整

    now = datetime.now(UTC)  # 过账完成时间
    order.status = "applied"  # 差异已过账
    order.completed_by = user_id  # 完成人即审批人
    order.completed_at = now  # 完成时间
    task = db.scalar(  # 同步更新对应审批任务
        select(ApprovalTask)  # 查询审批任务
        .where(  # 按业务类型+业务 ID 定位
            ApprovalTask.business_type == "stock_count",  # 盘点审批
            ApprovalTask.business_id == count_id,  # 本单
        )  # 结束 where
        .with_for_update()  # 加锁任务，避免与审批入口并发
    )  # 结束任务查询
    if task is not None and task.status == "pending":  # 仍待审才改，避免覆盖已决策
        task.status = "approved"  # 标为已同意
        task.decided_by = user_id  # 记录审批人
        task.decided_at = now  # 记录审批时间
    db.flush()  # 刷盘单据与任务
    refresh_count_freeze(db, _item_pairs(items))  # 过账后解冻/重算冻结
    body = _serialize_order(db, order)  # 序列化审批结果
    if record_idempotency:  # 直连接口才自己缓存幂等
        record_idempotent_response(  # 缓存同意响应
            db,  # 当前会话
            user_id=user_id,  # 操作者
            key=key,  # 幂等键
            method="POST",  # 同意方法
            path=path.format(count_id=count_id),  # 按调用方路径记录
            body=body,  # 响应体
            status=200,  # 成功状态码
        )  # 结束幂等缓存
    audit_after = {**body, "execution_items": execution_items}  # 审计附加执行账面，接口响应保持精简
    write_audit(  # 写同意过账审计
        db,  # 当前会话
        user_id=user_id,  # 操作者
        action="stock_count_approve",  # 审计动作
        entity_type="stock_count_order",  # 实体类型
        entity_id=count_id,  # 单据 ID
        before=before,  # 审批前
        after=audit_after,  # 审批后含执行快照
        request_id=request_id,  # 请求追踪
    )  # 结束审计写入
    if commit:  # 直连接口自己提交；审批入口则外层提交
        db.commit()  # 提交事务
    return ServiceResult(body, 200)  # 返回同意结果


def reject_stock_count(  # 审批驳回：不解账，只改状态并解冻
    db: Session,  # 数据库会话
    *,  # 后续必须关键字传参
    count_id: int,  # 盘点单 ID
    user_id: int,  # 审批人
    key: str | None,  # 幂等键
    comment: str | None = None,  # 驳回意见
    request_id: str = "api",  # 请求追踪 ID
    path: str = "/api/v1/stock-counts/{count_id}/reject",  # 幂等路径，审批入口可覆盖
    commit: bool = True,  # 审批服务调用时由外层提交
    record_idempotency: bool = True,  # 审批服务调用时由外层记幂等
) -> ServiceResult:  # 返回 body + HTTP 状态
    key = require_idempotency_key(key)  # 强制要求幂等键
    if record_idempotency:  # 直连盘点驳回接口时才自己做幂等
        prior = replay_result(db, user_id, key)  # 回放已成功的驳回结果
        if prior is not None:  # 命中幂等
            return prior  # 直接返回上次结果

    order = _locked_order(db, count_id)  # 加锁读取单据
    if order is None:  # 单据不存在
        raise AppError("STOCK_COUNT_NOT_FOUND", "盘点单不存在", 404)  # 返回 404
    before = _serialize_order(db, order)  # 驳回前快照
    if order.status != "pending_approval":  # 只有待审可驳回
        raise AppError("STOCK_COUNT_STATE_INVALID", "当前盘点单不可驳回", 409)  # 状态冲突

    items = list(  # 加载明细，供解冻使用
        db.scalars(  # 取明细实体
            select(StockCountItem).where(StockCountItem.stock_count_order_id == count_id)  # 按单据过滤明细
        )  # 结束 scalars
    )  # 结束明细列表
    now = datetime.now(UTC)  # 驳回时间
    order.status = "rejected"  # 单据标为驳回
    task = db.scalar(  # 同步更新对应审批任务
        select(ApprovalTask)  # 查询审批任务
        .where(  # 按业务类型+业务 ID 定位
            ApprovalTask.business_type == "stock_count",  # 盘点审批
            ApprovalTask.business_id == count_id,  # 本单
        )  # 结束 where
        .with_for_update()  # 加锁任务
    )  # 结束任务查询
    if task is not None and task.status == "pending":  # 仍待审才改
        task.status = "rejected"  # 标为已驳回
        task.decided_by = user_id  # 记录审批人
        task.decided_at = now  # 记录审批时间
        task.comment = comment  # 保存驳回意见
    db.flush()  # 刷盘单据与任务
    refresh_count_freeze(db, _item_pairs(items))  # 驳回后解除盘点冻结
    body = _serialize_order(db, order)  # 序列化驳回结果
    if record_idempotency:  # 直连接口才自己缓存幂等
        record_idempotent_response(  # 缓存驳回响应
            db,  # 当前会话
            user_id=user_id,  # 操作者
            key=key,  # 幂等键
            method="POST",  # 驳回方法
            path=path.format(count_id=count_id),  # 按调用方路径记录
            body=body,  # 响应体
            status=200,  # 成功状态码
        )  # 结束幂等缓存
    write_audit(  # 写驳回审计
        db,  # 当前会话
        user_id=user_id,  # 操作者
        action="stock_count_reject",  # 审计动作
        entity_type="stock_count_order",  # 实体类型
        entity_id=count_id,  # 单据 ID
        before=before,  # 驳回前
        after=body,  # 驳回后
        request_id=request_id,  # 请求追踪
    )  # 结束审计写入
    if commit:  # 直连接口自己提交；审批入口则外层提交
        db.commit()  # 提交事务
    return ServiceResult(body, 200)  # 返回驳回结果


def list_stock_counts(  # 分页列出当前用户可见的盘点单
    db: Session,  # 数据库会话
    *,  # 后续必须关键字传参
    user_id: int,  # 当前用户
    roles: set[str],  # 当前角色
    page: int = 1,  # 页码，从 1 开始
    page_size: int = 20,  # 每页条数
    status: str | None = None,  # 可选状态精确过滤
    order_no: str | None = None,  # 可选单号模糊搜索
) -> dict[str, Any]:  # 返回分页列表
    statement = select(StockCountOrder).order_by(StockCountOrder.stock_count_order_id.desc())  # 新单在前
    count_statement = select(func.count()).select_from(StockCountOrder)  # 同步的计数查询
    if status:  # 有状态过滤
        statement = statement.where(StockCountOrder.status == status)  # 列表按精确状态过滤
        count_statement = count_statement.where(StockCountOrder.status == status)  # 计数同样过滤
    if order_no:  # 单号模糊搜索
        statement = statement.where(StockCountOrder.order_no.ilike(f"%{order_no}%"))  # 忽略大小写包含
        count_statement = count_statement.where(StockCountOrder.order_no.ilike(f"%{order_no}%"))  # 计数同样过滤

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
        db.scalars(  # 执行分页查询
            statement.limit(page_size).offset((page - 1) * page_size)  # 按页切片
        )  # 结束 scalars
    )  # 结束本页列表
    return {  # 分页响应
        "items": [_serialize_order(db, row, include_items=False) for row in rows],  # 列表不带明细
        "total": total,  # 总条数
        "page": page,  # 当前页
        "page_size": page_size,  # 每页大小
    }  # 结束列表响应


def get_stock_count(  # 读取盘点单详情
    db: Session,  # 数据库会话
    count_id: int,  # 盘点单 ID
    *,  # 后续必须关键字传参
    user_id: int,  # 当前用户
    roles: set[str],  # 当前角色
) -> dict[str, Any]:  # 返回序列化单据
    order = db.get(StockCountOrder, count_id)  # 按主键读取单据
    if order is None:  # 单据不存在
        raise AppError("STOCK_COUNT_NOT_FOUND", "盘点单不存在", 404)  # 返回 404
    items = list(  # 加载明细供范围校验
        db.scalars(  # 取明细实体
            select(StockCountItem).where(StockCountItem.stock_count_order_id == count_id)  # 按单据过滤明细
        )  # 结束 scalars
    )  # 结束明细列表
    _ensure_order_read_scope(  # 详情也必须过仓库范围
        db,  # 当前会话
        order,  # 单据
        items,  # 明细
        user_id=user_id,  # 当前用户
        roles=roles,  # 当前角色
    )  # 结束范围校验
    return _serialize_order(db, order)  # 返回含明细的详情
