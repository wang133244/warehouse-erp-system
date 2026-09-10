from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.db.models import AuditLog
from backend.app.db.session import get_db
from backend.app.dependencies import get_current_user
router=APIRouter(prefix="/audit-logs",tags=["审计"])
@router.get("")
def list_logs(_:Annotated[object,Depends(get_current_user)],db:Annotated[Session,Depends(get_db)],limit:int=Query(100,ge=1,le=500)):
 rows=list(db.scalars(select(AuditLog).order_by(AuditLog.audit_log_id.desc()).limit(limit)))
 return {"items":[{"audit_log_id":r.audit_log_id,"action":r.action,"entity_type":r.entity_type,"entity_id":r.entity_id,"user_id":r.user_id,"created_at":r.created_at}for r in rows]}
