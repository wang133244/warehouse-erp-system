from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.app.db.models import DataImportBatch, Product, Warehouse, WarehouseLocation
from backend.app.db.session import get_db
from backend.app.dependencies import get_current_user
from backend.app.schemas.catalog import ImportBatchResponse, LocationResponse, ProductResponse, WarehouseResponse

router = APIRouter(tags=["基础资料"])


def _page(stmt, count_stmt, db: Session, offset: int, limit: int):
    return {"total": db.scalar(count_stmt) or 0, "items": list(db.scalars(stmt.offset(offset).limit(limit)))}


@router.get("/products")
def list_products(
    _: Annotated[object, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    keyword: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    where = []
    if keyword:
        like = f"%{keyword}%"
        where.append(or_(Product.sku_code.like(like), Product.product_name.like(like), Product.brand.like(like)))
    return _page(select(Product).where(*where).order_by(Product.product_id), select(func.count()).select_from(Product).where(*where), db, offset, limit)


@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, _: Annotated[object, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product


@router.get("/warehouses")
def list_warehouses(_: Annotated[object, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    return {"total": db.scalar(select(func.count()).select_from(Warehouse)) or 0, "items": list(db.scalars(select(Warehouse).order_by(Warehouse.warehouse_id)))}


@router.get("/locations")
def list_locations(
    _: Annotated[object, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    warehouse_id: int | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    where = [WarehouseLocation.warehouse_id == warehouse_id] if warehouse_id is not None else []
    return _page(select(WarehouseLocation).where(*where).order_by(WarehouseLocation.location_id), select(func.count()).select_from(WarehouseLocation).where(*where), db, offset, limit)


@router.get("/imports")
def list_imports(_: Annotated[object, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    return {"total": db.scalar(select(func.count()).select_from(DataImportBatch)) or 0, "items": list(db.scalars(select(DataImportBatch).order_by(DataImportBatch.batch_id.desc())))}


@router.get("/imports/{batch_id}", response_model=ImportBatchResponse)
def get_import(batch_id: int, _: Annotated[object, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    batch = db.get(DataImportBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="导入批次不存在")
    return batch
