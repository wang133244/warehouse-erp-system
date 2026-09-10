from __future__ import annotations
from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.core.errors import AppError
from backend.app.db.models import OutboundItem, OutboundOrder, PickingTask
from backend.app.schemas.outbounds import OutboundCreate
from backend.app.services.inventory_service import deduct_reserved, existing_idempotent_response, record_idempotent_response, require_idempotency_key, reserve, write_audit

def create_order(db:Session,payload:OutboundCreate,user_id:int,key:str)->dict:
 key=require_idempotency_key(key);prior=existing_idempotent_response(db,user_id,key)
 if prior:return prior
 if db.scalar(select(OutboundOrder).where(OutboundOrder.order_no==payload.order_no)):raise AppError("ORDER_NO_EXISTS","出库单号已存在",409)
 order=OutboundOrder(order_no=payload.order_no,customer_id=payload.customer_id,note=payload.note,created_by=user_id,status="draft");db.add(order);db.flush();db.add_all([OutboundItem(outbound_order_id=order.outbound_order_id,**x.model_dump()) for x in payload.items]);db.flush();body={"outbound_order_id":order.outbound_order_id,"order_no":order.order_no,"status":order.status};record_idempotent_response(db,user_id=user_id,key=key,path="/api/v1/outbounds",body=body,status=201);write_audit(db,user_id=user_id,action="outbound_create",entity_type="outbound_order",entity_id=order.outbound_order_id,after=body);db.commit();return body

def allocate_order(db:Session,order_id:int,user_id:int,key:str)->dict:
 key=require_idempotency_key(key);prior=existing_idempotent_response(db,user_id,key)
 if prior:return prior
 order=db.get(OutboundOrder,order_id)
 if order is None:raise AppError("NOT_FOUND","出库单不存在",404)
 if order.status!="draft":raise AppError("ORDER_STATE_INVALID","只有草稿出库单可以分配",409)
 tasks=[]
 for item in db.scalars(select(OutboundItem).where(OutboundItem.outbound_order_id==order_id)):
  allocations=reserve(db,product_id=item.product_id,quantity=item.quantity,source_id=order_id,key=key,user_id=user_id)
  item.allocated_quantity=item.quantity
  for location_id,qty in allocations:
   task=PickingTask(task_no=f"PK-{order_id}-{item.outbound_item_id}-{location_id}",outbound_order_id=order_id,outbound_item_id=item.outbound_item_id,product_id=item.product_id,location_id=location_id,quantity=qty,status="allocated");db.add(task);db.flush();tasks.append({"picking_task_id":task.picking_task_id,"location_id":location_id,"quantity":qty,"status":task.status})
 order.status="allocated";body={"outbound_order_id":order_id,"status":order.status,"tasks":tasks};record_idempotent_response(db,user_id=user_id,key=key,path=f"/api/v1/outbounds/{order_id}/allocate",body=body);db.commit();return body

def confirm_task(db:Session,task_id:int,user_id:int,key:str)->dict:
 key=require_idempotency_key(key);prior=existing_idempotent_response(db,user_id,key)
 if prior:return prior
 task=db.get(PickingTask,task_id)
 if task is None:raise AppError("NOT_FOUND","拣货任务不存在",404)
 if task.status!="allocated":raise AppError("TASK_STATE_INVALID","任务不可确认",409)
 task.status="picked";task.confirmed_by=user_id;task.confirmed_at=datetime.now(UTC);body={"picking_task_id":task_id,"status":task.status};record_idempotent_response(db,user_id=user_id,key=key,path=f"/api/v1/picking-tasks/{task_id}/confirm",body=body);db.commit();return body

def complete_order(db:Session,order_id:int,user_id:int,key:str)->dict:
 key=require_idempotency_key(key);prior=existing_idempotent_response(db,user_id,key)
 if prior:return prior
 order=db.get(OutboundOrder,order_id)
 if order is None:raise AppError("NOT_FOUND","出库单不存在",404)
 if order.status!="allocated":raise AppError("ORDER_STATE_INVALID","只有已分配出库单可以完成",409)
 tasks=list(db.scalars(select(PickingTask).where(PickingTask.outbound_order_id==order_id)))
 if not tasks or any(t.status!="picked" for t in tasks):raise AppError("TASK_NOT_CONFIRMED","所有拣货任务确认后才能完成",409)
 for task in tasks:deduct_reserved(db,product_id=task.product_id,location_id=task.location_id,quantity=task.quantity,source_id=order_id,key=key,user_id=user_id);task.status="completed"
 order.status="completed";order.completed_by=user_id;order.completed_at=datetime.now(UTC);body={"outbound_order_id":order_id,"status":order.status};record_idempotent_response(db,user_id=user_id,key=key,path=f"/api/v1/outbounds/{order_id}/complete",body=body);db.commit();return body
