from __future__ import annotations
from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.core.errors import AppError
from backend.app.db.models import InboundItem, InboundOrder
from backend.app.schemas.inbounds import InboundCreate
from backend.app.services.inventory_service import apply_inbound, existing_idempotent_response, record_idempotent_response, require_idempotency_key, write_audit

def create_order(db: Session, payload: InboundCreate, user_id: int, key: str) -> dict:
    key=require_idempotency_key(key); prior=existing_idempotent_response(db,user_id,key)
    if prior:return prior
    if db.scalar(select(InboundOrder).where(InboundOrder.order_no==payload.order_no)): raise AppError("ORDER_NO_EXISTS","入库单号已存在",409)
    order=InboundOrder(order_no=payload.order_no,note=payload.note,created_by=user_id,status="draft"); db.add(order);db.flush()
    db.add_all([InboundItem(inbound_order_id=order.inbound_order_id, **item.model_dump()) for item in payload.items]); db.flush()
    body={"inbound_order_id":order.inbound_order_id,"order_no":order.order_no,"status":order.status}; record_idempotent_response(db,user_id=user_id,key=key,path="/api/v1/inbounds",body=body,status=201);write_audit(db,user_id=user_id,action="inbound_create",entity_type="inbound_order",entity_id=order.inbound_order_id,after=body);db.commit();return body

def confirm_order(db: Session, order_id:int,user_id:int,key:str)->dict:
    key=require_idempotency_key(key);prior=existing_idempotent_response(db,user_id,key)
    if prior:return prior
    order=db.get(InboundOrder,order_id)
    if order is None:raise AppError("NOT_FOUND","入库单不存在",404)
    if order.status!="draft":raise AppError("ORDER_STATE_INVALID","只有草稿入库单可以确认",409)
    items=list(db.scalars(select(InboundItem).where(InboundItem.inbound_order_id==order_id)))
    for item in items: apply_inbound(db,product_id=item.product_id,location_id=item.location_id,quantity=item.quantity,source_id=order_id,key=key,user_id=user_id)
    order.status="confirmed";order.confirmed_by=user_id;order.confirmed_at=datetime.now(UTC);body={"inbound_order_id":order_id,"status":order.status};record_idempotent_response(db,user_id=user_id,key=key,path=f"/api/v1/inbounds/{order_id}/confirm",body=body);db.commit();return body
