from typing import Annotated
from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.db.models import InboundItem, InboundOrder
from backend.app.db.session import get_db
from backend.app.dependencies import get_current_user
from backend.app.schemas.inbounds import InboundCreate
from backend.app.services.inbound_service import confirm_order, create_order
router=APIRouter(prefix="/inbounds",tags=["入库"])
@router.get("")
def list_orders(_:Annotated[object,Depends(get_current_user)],db:Annotated[Session,Depends(get_db)]):
 rows=list(db.scalars(select(InboundOrder).order_by(InboundOrder.inbound_order_id.desc())))
 return {"items":[{"inbound_order_id":x.inbound_order_id,"order_no":x.order_no,"status":x.status,"note":x.note,"created_at":x.created_at} for x in rows]}
@router.post("",status_code=status.HTTP_201_CREATED)
def create(payload:InboundCreate,response:Response,current_user:Annotated[object,Depends(get_current_user)],db:Annotated[Session,Depends(get_db)],idempotency_key:Annotated[str|None,Header(alias="Idempotency-Key")]=None):
 body=create_order(db,payload,current_user.user_id,idempotency_key);response.status_code=201 if body.get("status")=="draft" else 200;return body
@router.get("/{order_id}")
def get_order(order_id:int,_:Annotated[object,Depends(get_current_user)],db:Annotated[Session,Depends(get_db)]):
 order=db.get(InboundOrder,order_id)
 if order is None: from backend.app.core.errors import AppError;raise AppError("NOT_FOUND","入库单不存在",404)
 items=list(db.scalars(select(InboundItem).where(InboundItem.inbound_order_id==order_id)))
 return {"inbound_order_id":order.inbound_order_id,"order_no":order.order_no,"status":order.status,"note":order.note,"items":[{"inbound_item_id":i.inbound_item_id,"product_id":i.product_id,"location_id":i.location_id,"quantity":i.quantity}for i in items]}
@router.post("/{order_id}/confirm")
def confirm(order_id:int,current_user:Annotated[object,Depends(get_current_user)],db:Annotated[Session,Depends(get_db)],idempotency_key:Annotated[str|None,Header(alias="Idempotency-Key")]=None):return confirm_order(db,order_id,current_user.user_id,idempotency_key)
