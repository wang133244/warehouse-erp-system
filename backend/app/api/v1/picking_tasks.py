from typing import Annotated
from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.db.models import PickingTask
from backend.app.db.session import get_db
from backend.app.dependencies import get_current_user
from backend.app.services.outbound_service import confirm_task
router=APIRouter(prefix="/picking-tasks",tags=["拣货"])
@router.get("")
def list_tasks(_:Annotated[object,Depends(get_current_user)],db:Annotated[Session,Depends(get_db)]):
 rows=list(db.scalars(select(PickingTask).order_by(PickingTask.picking_task_id.desc())))
 return {"items":[{"picking_task_id":x.picking_task_id,"task_no":x.task_no,"outbound_order_id":x.outbound_order_id,"product_id":x.product_id,"location_id":x.location_id,"quantity":x.quantity,"status":x.status}for x in rows]}
@router.post("/{task_id}/confirm")
def confirm(task_id:int,current_user:Annotated[object,Depends(get_current_user)],db:Annotated[Session,Depends(get_db)],idempotency_key:Annotated[str|None,Header(alias="Idempotency-Key")]=None):return confirm_task(db,task_id,current_user.user_id,idempotency_key)
