from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from backend.app.db.models import StockBalance
from backend.app.db.session import get_db
from backend.app.dependencies import get_current_user
router=APIRouter(prefix="/alerts",tags=["预警"])
@router.get("")
def alerts(_:Annotated[object,Depends(get_current_user)],db:Annotated[Session,Depends(get_db)],threshold:int=Query(10,ge=0)):
 rows=list(db.scalars(select(StockBalance).where(StockBalance.quantity-StockBalance.reserved_quantity<=threshold).order_by(StockBalance.quantity)))
 return {"threshold":threshold,"items":[{"balance_id":r.balance_id,"product_id":r.product_id,"location_id":r.location_id,"quantity":r.quantity,"reserved_quantity":r.reserved_quantity,"available_quantity":r.quantity-r.reserved_quantity}for r in rows]}
