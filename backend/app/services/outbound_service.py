"""出库分配预留、复核、完成扣账。"""

from __future__ import annotations  # 启用延后求值类型注解

from datetime import UTC, datetime  # 拣货确认/复核/完成写入 UTC 时间

from sqlalchemy import select  # 查出库单、明细与拣货任务
from sqlalchemy.orm import Session  # 同一事务内预留或扣账

from backend.app.core.errors import AppError  # 状态非法、任务未确认等错误
from backend.app.models import OutboundItem, OutboundOrder, PickingTask  # 出库单、明细、拣货任务
from backend.app.dependencies import get_current_user_roles, require_granted_warehouses  # 授权仓库，限制分配范围
from backend.app.schemas.outbounds import OutboundCreate, OutboundReview  # 创建与复核入参
from backend.app.services.catalog_service import require_usable_product  # 停用商品不能出库
from backend.app.services.inventory_service import (  # 预留与扣账都走唯一写库存服务
    deduct_reserved,  # 完成出库：扣实际+预留
    existing_idempotent_response,  # 幂等回放，避免重复预留/重复扣账
    record_idempotent_response,  # 成功后记录响应
    require_idempotency_key,  # 写操作强制幂等键
    reserve,  # 分配阶段只加预留，不扣实际库存
    write_audit,  # 建单/复核审计
)  # 结束库存服务导入：分配预留、完成才扣账


def create_order(db: Session, payload: OutboundCreate, user_id: int, key: str) -> dict:  # 创建出库草稿，此时不预留也不扣库存
    key = require_idempotency_key(key)  # 强制幂等键，防止连点建两张单
    prior = existing_idempotent_response(db, user_id, key)  # 已创建则回放
    if prior:  # 幂等命中
        return prior  # 返回上次建单结果
    if db.scalar(select(OutboundOrder).where(OutboundOrder.order_no == payload.order_no)):  # 出库单号唯一
        raise AppError("ORDER_NO_EXISTS", "出库单号已存在", 409)  # 单号冲突
    roles = get_current_user_roles(db, user_id)  # 取角色
    require_granted_warehouses(db, user_id, roles)  # 必须有授权仓才能建出库单
    for item in payload.items:  # 逐行校验商品
        require_usable_product(db, item.product_id)  # 停用商品不能出库
    order = OutboundOrder(  # 构造草稿出库单
        order_no=payload.order_no,  # 业务单号
        customer_id=payload.customer_id,  # 客户
        note=payload.note,  # 备注
        created_by=user_id,  # 创建人
        status="draft",  # 草稿：尚未预留库存
    )  # 结束单头
    db.add(order)  # 插入单头
    db.flush()  # 拿到 outbound_order_id
    db.add_all(  # 批量插明细
        [OutboundItem(outbound_order_id=order.outbound_order_id, **item.model_dump()) for item in payload.items]  # schema 落到出库明细
    )  # 结束批量插入
    db.flush()  # 确保明细已写入
    body = {  # 创建返回体
        "outbound_order_id": order.outbound_order_id,  # 新单 ID
        "order_no": order.order_no,  # 单号
        "status": order.status,  # draft
    }  # 结束返回体
    record_idempotent_response(db, user_id=user_id, key=key, path="/api/v1/outbounds", body=body, status=201)  # 记下 201
    write_audit(  # 审计建单（库存未变）
        db,  # 同一事务
        user_id=user_id,  # 创建人
        action="outbound_create",  # 创建出库草稿
        entity_type="outbound_order",  # 实体出库单
        entity_id=order.outbound_order_id,  # 新单 ID
        after=body,  # 创建快照
    )  # 结束审计
    db.commit()  # 提交草稿，不改库存
    return body  # 返回创建结果


def allocate_order(db: Session, order_id: int, user_id: int, key: str) -> dict:  # 分配：reserve 占用预留，生成拣货任务
    key = require_idempotency_key(key)  # 分配必须幂等，防止重复预留
    prior = existing_idempotent_response(db, user_id, key)  # 已分配则回放
    if prior:  # 幂等命中
        return prior  # 不再二次预留
    order = db.get(OutboundOrder, order_id)  # 加载出库单
    if order is None:  # 单不存在
        raise AppError("NOT_FOUND", "出库单不存在", 404)  # 404
    if order.status != "draft":  # 只有草稿可分配
        raise AppError("ORDER_STATE_INVALID", "只有草稿出库单可以分配", 409)  # 防止已分配单再占预留
    tasks = []  # 收集生成的拣货任务摘要
    roles = get_current_user_roles(db, user_id)  # 取角色
    granted = require_granted_warehouses(db, user_id, roles)  # 授权仓库集合，reserve 只从这些仓找货
    for item in db.scalars(select(OutboundItem).where(OutboundItem.outbound_order_id == order_id)):  # 逐行分配
        require_usable_product(db, item.product_id)  # 再次确认商品可用
        allocations = reserve(  # 调用唯一库存服务：只增加 reserved_quantity，不扣实际库存
            db,  # 同一事务
            product_id=item.product_id,  # 商品
            quantity=item.quantity,  # 需求数量，不足则整单失败
            source_id=order_id,  # 出库单 ID 写入审计
            key=key,  # 幂等键随预留链路传递
            user_id=user_id,  # 操作人
            warehouse_ids=granted,  # 限制授权仓，避免跨仓超卖别人的货
        )  # 得到 [(库位, 数量)]
        item.allocated_quantity = item.quantity  # 分配成功则已分配量=需求量
        for location_id, qty in allocations:  # 每个库位一条拣货任务
            task = PickingTask(  # 构造拣货任务
                task_no=f"PK-{order_id}-{item.outbound_item_id}-{location_id}",  # 任务号含单、明细、库位
                outbound_order_id=order_id,  # 归属出库单
                outbound_item_id=item.outbound_item_id,  # 归属明细
                product_id=item.product_id,  # 商品
                location_id=location_id,  # 从该库位拣
                quantity=qty,  # 本库位预留数量
                status="allocated",  # 已分配待拣
            )  # 结束任务字段
            db.add(task)  # 插入任务
            db.flush()  # 拿到 picking_task_id
            tasks.append(  # 放入返回列表
                {  # 任务摘要
                    "picking_task_id": task.picking_task_id,  # 任务 ID
                    "location_id": location_id,  # 库位
                    "quantity": qty,  # 数量
                    "status": task.status,  # allocated
                }  # 结束摘要
            )  # 结束 append
    order.status = "allocated"  # 单头改为已分配
    body = {"outbound_order_id": order_id, "status": order.status, "tasks": tasks}  # 分配结果
    record_idempotent_response(  # 记下分配结果，同键不再重复预留
        db, user_id=user_id, key=key, path=f"/api/v1/outbounds/{order_id}/allocate", body=body  # 路径含单号
    )  # 结束幂等记录
    db.commit()  # 提交预留与任务
    return body  # 返回分配结果


def confirm_task(db: Session, task_id: int, user_id: int, key: str) -> dict:  # 拣货确认：只改任务/已拣数量，不扣库存
    key = require_idempotency_key(key)  # 确认拣货也要幂等
    prior = existing_idempotent_response(db, user_id, key)  # 已确认则回放
    if prior:  # 幂等命中
        return prior  # 避免重复累加 picked_quantity
    task = db.get(PickingTask, task_id)  # 加载拣货任务
    if task is None:  # 任务不存在
        raise AppError("NOT_FOUND", "拣货任务不存在", 404)  # 404
    if task.status != "allocated":  # 只有已分配待拣可确认
        raise AppError("TASK_STATE_INVALID", "任务不可确认", 409)  # 防止重复确认
    task.status = "picked"  # 标记已拣，库存仍保持预留
    task.confirmed_by = user_id  # 拣货确认人
    task.confirmed_at = datetime.now(UTC)  # 确认时间
    item = db.get(OutboundItem, task.outbound_item_id)  # 回写明细已拣量
    if item is not None:  # 明细仍在
        item.picked_quantity = (item.picked_quantity or 0) + task.quantity  # 累加本任务数量
    order = db.get(OutboundOrder, task.outbound_order_id)  # 可能把整单推进到已拣货
    tasks = list(db.scalars(select(PickingTask).where(PickingTask.outbound_order_id == task.outbound_order_id)))  # 该单全部任务
    if order is not None and tasks and all(row.status == "picked" for row in tasks):  # 全部拣完才改单头
        order.status = "picked"  # 进入待复核，仍未扣实际库存
    body = {  # 确认返回体
        "picking_task_id": task_id,  # 任务 ID
        "status": task.status,  # picked
        "order_status": order.status if order is not None else None,  # 当前单头状态
    }  # 结束返回体
    record_idempotent_response(  # 记下拣货确认结果
        db, user_id=user_id, key=key, path=f"/api/v1/picking-tasks/{task_id}/confirm", body=body  # 任务确认路径
    )  # 结束幂等
    db.commit()  # 提交任务状态，不调用扣账
    return body  # 返回确认结果


def list_reviews(db: Session, keyword: str | None = None) -> dict:  # 只读：待复核/已复核出库单
    orders = list(  # 取出拣完或已复核的单
        db.scalars(  # 标量为出库单
            select(OutboundOrder)  # 查出库单
            .where(OutboundOrder.status.in_(("picked", "reviewed")))  # 复核工作台只看这两态
            .order_by(OutboundOrder.outbound_order_id.desc())  # 新单在前
        )  # 结束查询
    )  # 物化
    items = []  # 组装带明细和任务的复核列表
    for order in orders:  # 逐单加载
        lines = list(  # 出库明细
            db.scalars(select(OutboundItem).where(OutboundItem.outbound_order_id == order.outbound_order_id))  # 该单明细
        )  # 物化明细
        tasks = list(  # 拣货任务
            db.scalars(select(PickingTask).where(PickingTask.outbound_order_id == order.outbound_order_id))  # 该单任务
        )  # 物化任务
        items.append(  # 拼一条复核单
            {  # 单头+行+任务
                "outbound_order_id": order.outbound_order_id,  # 单 ID
                "order_no": order.order_no,  # 单号
                "status": order.status,  # picked 或 reviewed
                "customer_id": order.customer_id,  # 客户
                "review_comment": order.review_comment,  # 复核意见
                "items": [  # 明细
                    {  # 一行
                        "outbound_item_id": line.outbound_item_id,  # 明细 ID
                        "product_id": line.product_id,  # 商品
                        "quantity": line.quantity,  # 需求
                        "allocated_quantity": line.allocated_quantity,  # 已分配
                        "picked_quantity": line.picked_quantity,  # 已拣
                    }  # 结束一行
                    for line in lines  # 遍历明细
                ],  # 结束明细
                "tasks": [  # 拣货任务
                    {  # 一任务
                        "picking_task_id": task.picking_task_id,  # 任务 ID
                        "task_no": task.task_no,  # 任务号
                        "location_id": task.location_id,  # 库位
                        "quantity": task.quantity,  # 数量
                        "status": task.status,  # 任务状态
                    }  # 结束任务
                    for task in tasks  # 遍历任务
                ],  # 结束任务列表
            }  # 结束单对象
        )  # 结束 append
    if keyword:  # 关键字过滤单号、客户、状态中文
        needle = keyword.strip().lower()  # 规范化检索词
        items = [  # 内存过滤
            item  # 保留命中项
            for item in items  # 遍历已组装列表
            if needle in str(item["order_no"]).lower()  # 单号
            or needle in str(item.get("customer_id") or "")  # 客户 ID
            or needle in str(item["status"]).lower()  # 状态码
            or needle in ("待复核" if item["status"] == "picked" else "")  # 中文：待复核
            or needle in ("已复核" if item["status"] == "reviewed" else "")  # 中文：已复核
        ]  # 结束过滤
    return {"total": len(items), "items": items}  # 只读返回


def review_order(db: Session, order_id: int, user_id: int, key: str, payload: OutboundReview) -> dict:  # 复核通过：改状态与意见，不扣库存
    key = require_idempotency_key(key)  # 复核写操作要幂等
    prior = existing_idempotent_response(db, user_id, key)  # 已复核则回放
    if prior:  # 幂等命中
        return prior  # 不再改状态
    order = db.get(OutboundOrder, order_id)  # 加载出库单
    if order is None:  # 不存在
        raise AppError("NOT_FOUND", "出库单不存在", 404)  # 404
    if order.status != "picked":  # 只有已拣货可复核
        raise AppError("ORDER_STATE_INVALID", "只有已拣货出库单可以复核", 409)  # 状态门禁
    order.status = "reviewed"  # 标记已复核，仍保持预留
    order.reviewed_by = user_id  # 复核人
    order.reviewed_at = datetime.now(UTC)  # 复核时间
    order.review_comment = payload.comment  # 复核意见
    body = {"outbound_order_id": order_id, "status": order.status, "review_comment": order.review_comment}  # 返回体
    record_idempotent_response(  # 记下复核结果
        db, user_id=user_id, key=key, path=f"/api/v1/outbounds/{order_id}/review", body=body  # 复核路径
    )  # 结束幂等
    write_audit(  # 审计复核（库存数量不变）
        db,  # 同一事务
        user_id=user_id,  # 复核人
        action="outbound_review",  # 复核动作
        entity_type="outbound_order",  # 出库单
        entity_id=order_id,  # 单 ID
        after=body,  # 复核后快照
    )  # 结束审计
    db.commit()  # 提交状态，不扣账
    return body  # 返回复核结果


def complete_order(db: Session, order_id: int, user_id: int, key: str) -> dict:  # 完成出库：逐任务 deduct_reserved 真正扣库存
    key = require_idempotency_key(key)  # 完成必须幂等，防止重复扣账
    prior = existing_idempotent_response(db, user_id, key)  # 已完成则回放
    if prior:  # 幂等命中
        return prior  # 绝不二次扣实际库存
    order = db.get(OutboundOrder, order_id)  # 加载出库单
    if order is None:  # 不存在
        raise AppError("NOT_FOUND", "出库单不存在", 404)  # 404
    if order.status != "reviewed":  # 必须先复核
        raise AppError("ORDER_STATE_INVALID", "只有已复核出库单可以完成", 409)  # 门禁
    tasks = list(db.scalars(select(PickingTask).where(PickingTask.outbound_order_id == order_id)))  # 该单全部拣货任务
    if not tasks or any(task.status != "picked" for task in tasks):  # 任务缺失或未全部拣货确认
        raise AppError("TASK_NOT_CONFIRMED", "所有拣货任务确认后才能完成", 409)  # 禁止部分扣账
    for task in tasks:  # 按库位逐条扣账
        deduct_reserved(  # 唯一扣账入口：实际与预留同时减少并写 outbound 流水
            db,  # 同一事务
            product_id=task.product_id,  # 商品
            location_id=task.location_id,  # 库位
            quantity=task.quantity,  # 本任务数量
            source_id=order_id,  # 出库单
            key=key,  # 幂等键编入流水
            user_id=user_id,  # 完成人
        )  # 结束一条扣账
        task.status = "completed"  # 任务标记完成
    order.status = "completed"  # 单头完成
    order.completed_by = user_id  # 完成人
    order.completed_at = datetime.now(UTC)  # 完成时间
    body = {"outbound_order_id": order_id, "status": order.status}  # 返回体
    record_idempotent_response(  # 记下完成结果，同键不再扣库存
        db, user_id=user_id, key=key, path=f"/api/v1/outbounds/{order_id}/complete", body=body  # 完成路径
    )  # 结束幂等
    db.commit()  # 提交扣账与状态
    return body  # 返回完成结果
