from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from backend.app.db.models import StockBalance, StockLedger
from backend.app.db.session import get_db
from backend.app.dependencies import get_current_user
router=APIRouter(prefix="/inventory",tags=["库存"])
@router.get("/balances")
def balances(_:Annotated[object,Depends(get_current_user)],db:Annotated[Session,Depends(get_db)],product_id:int|None=None,offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=200)):
 where=[StockBalance.product_id==product_id] if product_id else []
 rows=list(db.scalars(select(StockBalance).where(*where).order_by(StockBalance.balance_id).offset(offset).limit(limit)))
 return {"total":db.scalar(select(func.count()).select_from(StockBalance).where(*where)) or 0,"items":[{"balance_id":x.balance_id,"product_id":x.product_id,"location_id":x.location_id,"quantity":x.quantity,"reserved_quantity":x.reserved_quantity,"available_quantity":x.quantity-x.reserved_quantity} for x in rows]}
@router.get("/{product_id}/availability")
def availability(product_id:int,_:Annotated[object,Depends(get_current_user)],db:Annotated[Session,Depends(get_db)]):
 quantity,reserved=db.execute(select(func.coalesce(func.sum(StockBalance.quantity),0),func.coalesce(func.sum(StockBalance.reserved_quantity),0)).where(StockBalance.product_id==product_id)).one()
 return {"product_id":product_id,"quantity":int(quantity),"reserved_quantity":int(reserved),"available_quantity":int(quantity-reserved)}
@router.get("/ledgers")
def ledgers(_:Annotated[object,Depends(get_current_user)],db:Annotated[Session,Depends(get_db)],limit:int=Query(100,ge=1,le=500)):
 rows=list(db.scalars(select(StockLedger).order_by(StockLedger.ledger_id.desc()).limit(limit)))
 return {"items":[{"ledger_id":r.ledger_id,"product_id":r.product_id,"location_id":r.location_id,"transaction_type":r.transaction_type,"quantity_delta":r.quantity_delta,"before_quantity":r.before_quantity,"after_quantity":r.after_quantity,"source_type":r.source_type,"source_id":r.source_id,"created_at":r.created_at} for r in rows]}
