"""入库草稿与收货确认；加库存调用 inventory_service。"""

from __future__ import annotations  # 启用延后求值类型注解

from datetime import UTC, datetime  # 确认收货时写入 UTC 确认时间

from sqlalchemy import or_, select  # or_ 用于关键字模糊搜单，select 查入库单
from sqlalchemy.orm import Session  # 数据库会话，草稿与确认在同一事务

from backend.app.core.errors import AppError  # 单号冲突、状态非法等业务错误
from backend.app.models import InboundItem, InboundOrder, Product, WarehouseLocation  # 入库单、明细及搜单用主数据
from backend.app.dependencies import ensure_warehouse_scope, get_current_user_roles, require_granted_warehouses  # 仓库授权校验
from backend.app.schemas.inbounds import InboundCreate, ReceiveConfirm  # 创建草稿与收货确认入参
from backend.app.services.catalog_service import require_usable_location, require_usable_product  # 校验商品/库位可用
from backend.app.services.user_service import account_name  # 把用户 ID 转成展示名
from backend.app.services.inventory_service import (  # 入库只在确认时调用唯一写库存入口
    apply_inbound,  # 真正加库存：行锁改余额、写流水
    existing_idempotent_response,  # 查幂等缓存，避免重复建单/重复收货
    record_idempotent_response,  # 成功后记下响应供回放
    require_idempotency_key,  # 写操作必须带幂等键
    write_audit,  # 记录入库创建/确认审计
)  # 结束库存服务导入：确认收货才加库存


def _order_body(db: Session, order: InboundOrder, items: list[InboundItem] | None = None) -> dict:  # 组装入库单对外 JSON，不改库存
    payload = {  # 单据头字段
        "inbound_order_id": order.inbound_order_id,  # 入库单主键
        "order_no": order.order_no,  # 业务单号
        "status": order.status,  # 草稿或已确认
        "note": order.note,  # 备注
        "created_at": order.created_at,  # 创建时间
        "username": account_name(db, order.confirmed_by or order.created_by),  # 确认人优先，否则创建人
    }  # 结束单据头
    if items is not None:  # 调用方传入明细才展开行，列表页可省略
        payload["items"] = [  # 收货明细列表
            {  # 单行明细
                "inbound_item_id": item.inbound_item_id,  # 明细主键
                "product_id": item.product_id,  # 商品
                "location_id": item.location_id,  # 收货库位
                "quantity": item.quantity,  # 应收/实收数量
            }  # 结束一行
            for item in items  # 遍历明细
        ]  # 结束明细列表
    return payload  # 只读组装结果，不写库存


def _validate_inbound_items(db: Session, items: list, user_id: int) -> None:  # 校验商品库位可用且落在授权仓
    roles = get_current_user_roles(db, user_id)  # 取当前用户角色
    require_granted_warehouses(db, user_id, roles)  # 必须已授予至少一个仓库
    warehouse_ids: set[int] = set()  # 收集明细涉及的仓库
    for item in items:  # 逐行校验
        product_id = item.product_id if hasattr(item, "product_id") else item["product_id"]  # 兼容对象或字典明细
        location_id = item.location_id if hasattr(item, "location_id") else item["location_id"]  # 兼容对象或字典库位
        require_usable_product(db, product_id)  # 停用商品不能入库
        location = require_usable_location(db, location_id)  # 停用库位不能收货
        warehouse_ids.add(location.warehouse_id)  # 记下该库位所属仓
    ensure_warehouse_scope(db, user_id, roles, warehouse_ids)  # 明细仓库必须都在授权范围内


def create_order(db: Session, payload: InboundCreate, user_id: int, key: str) -> dict:  # 创建入库草稿，此时不加库存
    key = require_idempotency_key(key)  # 强制幂等键，防止连点建两张单
    prior = existing_idempotent_response(db, user_id, key)  # 查是否已成功创建过
    if prior:  # 相同键直接回放，不再插单
        return prior  # 返回上次创建结果
    if db.scalar(select(InboundOrder).where(InboundOrder.order_no == payload.order_no)):  # 业务单号全局唯一
        raise AppError("ORDER_NO_EXISTS", "入库单号已存在", 409)  # 单号冲突
    _validate_inbound_items(db, payload.items, user_id)  # 校验明细商品库位与仓库权限
    order = InboundOrder(order_no=payload.order_no, note=payload.note, created_by=user_id, status="draft")  # 草稿状态，确认前不改库存
    db.add(order)  # 插入入库单头
    db.flush()  # 拿到 inbound_order_id 供明细外键
    db.add_all(  # 批量插入明细
        [InboundItem(inbound_order_id=order.inbound_order_id, **item.model_dump()) for item in payload.items]  # 把 schema 行落到明细表
    )  # 结束批量插入
    db.flush()  # 确保明细已写入本事务
    body = {  # 创建接口返回体
        "inbound_order_id": order.inbound_order_id,  # 新单 ID
        "order_no": order.order_no,  # 单号
        "status": order.status,  # 仍为 draft
    }  # 结束返回体
    record_idempotent_response(db, user_id=user_id, key=key, path="/api/v1/inbounds", body=body, status=201)  # 记下 201 供回放
    write_audit(  # 审计建单，此时库存未变
        db,  # 同一事务
        user_id=user_id,  # 创建人
        action="inbound_create",  # 动作：创建入库草稿
        entity_type="inbound_order",  # 实体入库单
        entity_id=order.inbound_order_id,  # 新单 ID
        after=body,  # 创建后快照
    )  # 结束审计
    db.commit()  # 提交草稿单据，仍不加库存
    return body  # 返回创建结果


def list_orders(db: Session, keyword: str | None = None, status: str | None = None) -> dict:  # 只读列出入库单
    statement = select(InboundOrder)  # 基础查询入库单头
    if status:  # 按状态筛选草稿/已确认
        statement = statement.where(InboundOrder.status == status)  # 精确匹配状态码
    if keyword:  # 关键字同时搜单号、状态、SKU、库位
        like = f"%{keyword.strip()}%"  # 模糊匹配模式
        status_alias = {"草稿": "draft", "已确认": "confirmed"}.get(keyword.strip())  # 中文状态映射到存储值
        matching_ids = (  # 子查询：明细商品/库位命中的入库单
            select(InboundItem.inbound_order_id)  # 只要单头 ID
            .join(Product, Product.product_id == InboundItem.product_id)  # 关联商品
            .join(WarehouseLocation, WarehouseLocation.location_id == InboundItem.location_id)  # 关联库位
            .where(  # SKU、来源码、品名、库位码任一模糊命中
                or_(  # 多字段 OR
                    Product.sku_code.like(like),  # 系统 SKU
                    Product.source_product_code.like(like),  # 来源商品编码
                    Product.product_name.like(like),  # 品名
                    WarehouseLocation.location_code.like(like),  # 库位码
                )  # 结束明细侧条件
            )  # 结束 where
        )  # 结束子查询
        filters = [  # 单头侧过滤条件
            InboundOrder.order_no.like(like),  # 单号模糊
            InboundOrder.status.like(like),  # 状态码模糊（draft 等）
            InboundOrder.inbound_order_id.in_(matching_ids),  # 或明细命中
        ]  # 结束条件列表
        if status_alias:  # 用户输入了中文状态别名
            filters.append(InboundOrder.status == status_alias)  # 再按映射后的状态精确匹配
        statement = statement.where(or_(*filters))  # 以上条件任一满足即入选
    rows = list(db.scalars(statement.order_by(InboundOrder.inbound_order_id.desc())))  # 新单在前
    return {  # 列表响应
        "total": len(rows),  # 条数
        "items": [  # 单据摘要
            {  # 一行列表
                "inbound_order_id": row.inbound_order_id,  # 主键
                "order_no": row.order_no,  # 单号
                "status": row.status,  # 状态
                "note": row.note,  # 备注
                "created_at": row.created_at,  # 创建时间
                "username": account_name(db, row.confirmed_by or row.created_by),  # 展示操作人
            }  # 结束一行
            for row in rows  # 遍历结果
        ],  # 结束 items
    }  # 结束列表响应


def list_receivings(db: Session) -> dict:  # 待收货列表：仅草稿入库单带明细
    orders = list(  # 取出所有草稿入库单
        db.scalars(  # 标量结果为订单对象
            select(InboundOrder)  # 查入库单
            .where(InboundOrder.status == "draft")  # 只有草稿才能收货确认
            .order_by(InboundOrder.inbound_order_id.desc())  # 新单优先
        )  # 结束查询
    )  # 物化为列表
    items = []  # 组装带明细的待收货单
    for order in orders:  # 逐单加载明细
        lines = list(db.scalars(select(InboundItem).where(InboundItem.inbound_order_id == order.inbound_order_id)))  # 该单全部收货行
        items.append(_order_body(db, order, lines))  # 把头+行拼进响应
    return {"total": len(items), "items": items}  # 只读返回，不改库存


def confirm_order(  # 收货确认：此时才调用 apply_inbound 加库存
    db: Session,  # 当前事务，单据状态与库存同提交
    order_id: int,  # 要确认的入库单
    user_id: int,  # 确认人
    key: str,  # 幂等键，防止重复加库存
    payload: ReceiveConfirm | None = None,  # 可选：改备注或实收数量
) -> dict:  # 返回确认后状态
    key = require_idempotency_key(key)  # 确认必须带幂等键
    prior = existing_idempotent_response(db, user_id, key)  # 已确认过则回放，不再加库存
    if prior:  # 幂等命中
        return prior  # 直接返回上次确认结果
    order = db.get(InboundOrder, order_id)  # 按主键加载入库单
    if order is None:  # 单不存在
        raise AppError("NOT_FOUND", "入库单不存在", 404)  # 404
    if order.status != "draft":  # 已确认不能再确认，避免二次加库存
        raise AppError("ORDER_STATE_INVALID", "只有草稿入库单可以确认", 409)  # 状态冲突
    items = list(db.scalars(select(InboundItem).where(InboundItem.inbound_order_id == order_id)))  # 加载全部明细准备过账
    _validate_inbound_items(db, items, user_id)  # 再次校验权限与主数据
    if payload and payload.note is not None:  # 确认时可改备注
        order.note = payload.note  # 更新备注
    if payload and payload.items:  # 确认时可按实收改数量
        by_id = {item.inbound_item_id: item for item in items}  # 明细 ID 索引
        for line in payload.items:  # 逐行套用实收
            item = by_id.get(line.inbound_item_id)  # 必须属于本单
            if item is None:  # 明细不属于当前入库单
                raise AppError("ITEM_NOT_FOUND", "收货明细不属于当前入库单", 400)  # 拒绝脏数据
            item.quantity = line.received_quantity  # 用实收覆盖原数量，后续按此加库存
    for item in items:  # 逐行过账
        if item.quantity > 0:  # 数量为 0 的行不加库存
            apply_inbound(  # 唯一写库存入口：加实际数量、写流水与审计
                db,  # 同一事务
                product_id=item.product_id,  # 商品
                location_id=item.location_id,  # 收货库位
                quantity=item.quantity,  # 实收数量
                source_id=order_id,  # 来源入库单
                key=key,  # 幂等键编入流水，防同键重复过账
                user_id=user_id,  # 确认人
            )  # 结束一行入库过账
    order.status = "confirmed"  # 单据改为已确认
    order.confirmed_by = user_id  # 记录确认人
    order.confirmed_at = datetime.now(UTC)  # 记录确认时间（UTC）
    body = {"inbound_order_id": order_id, "status": order.status}  # 确认接口返回体
    path = f"/api/v1/inbounds/{order_id}/confirm"  # 幂等记录对应的路径
    record_idempotent_response(db, user_id=user_id, key=key, path=path, body=body)  # 保存成功结果，下次同键不再加库存
    write_audit(  # 审计入库确认
        db,  # 同一事务
        user_id=user_id,  # 确认人
        action="inbound_confirm",  # 动作：确认收货
        entity_type="inbound_order",  # 实体入库单
        entity_id=order_id,  # 单 ID
        after=body,  # 确认后状态
    )  # 结束审计
    db.commit()  # 一次性提交单据状态与库存增加
    return body  # 返回确认结果
