from typing import Annotated
from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.db.models import OutboundItem, OutboundOrder
from backend.app.db.session import get_db
from backend.app.dependencies import get_current_user
from backend.app.schemas.outbounds import OutboundCreate
from backend.app.services.outbound_service import allocate_order, complete_order, create_order
router=APIRouter(prefix="/outbounds",tags=["出库"])
@router.get("")
def list_orders(_:Annotated[object,Depends(get_current_user)],db:Annotated[Session,Depends(get_db)]):
 rows=list(db.scalars(select(OutboundOrder).order_by(OutboundOrder.outbound_order_id.desc())))
 return {"items":[{"outbound_order_id":x.outbound_order_id,"order_no":x.order_no,"status":x.status,"customer_id":x.customer_id,"note":x.note,"created_at":x.created_at}for x in rows]}
@router.post("",status_code=status.HTTP_201_CREATED)
def create(payload:OutboundCreate,response:Response,current_user:Annotated[object,Depends(get_current_user)],db:Annotated[Session,Depends(get_db)],idempotency_key:Annotated[str|None,Header(alias="Idempotency-Key")]=None):
 body=create_order(db,payload,current_user.user_id,idempotency_key);response.status_code=201 if body.get("status")=="draft"else 200;return body
@router.get("/{order_id}")
def get_order(order_id:int,_:Annotated[object,Depends(get_current_user)],db:Annotated[Session,Depends(get_db)]):
 order=db.get(OutboundOrder,order_id)
 if order is None:from backend.app.core.errors import AppError;raise AppError("NOT_FOUND","出库单不存在",404)
 items=list(db.scalars(select(OutboundItem).where(OutboundItem.outbound_order_id==order_id)))
 return {"outbound_order_id":order.outbound_order_id,"order_no":order.order_no,"status":order.status,"items":[{"outbound_item_id":i.outbound_item_id,"product_id":i.product_id,"quantity":i.quantity,"allocated_quantity":i.allocated_quantity,"picked_quantity":i.picked_quantity}for i in items]}
@router.post("/{order_id}/allocate")
def allocate(order_id:int,current_user:Annotated[object,Depends(get_current_user)],db:Annotated[Session,Depends(get_db)],idempotency_key:Annotated[str|None,Header(alias="Idempotency-Key")]=None):return allocate_order(db,order_id,current_user.user_id,idempotency_key)
@router.post("/{order_id}/complete")
def complete(order_id:int,current_user:Annotated[object,Depends(get_current_user)],db:Annotated[Session,Depends(get_db)],idempotency_key:Annotated[str|None,Header(alias="Idempotency-Key")]=None):return complete_order(db,order_id,current_user.user_id,idempotency_key)
