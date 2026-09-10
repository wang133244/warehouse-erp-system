from datetime import datetime
from pydantic import BaseModel


class ProductResponse(BaseModel):
    product_id: int
    sku_code: str
    source_product_code: str
    brand: str
    product_name: str
    category: str
    size: str
    function_feature: str
    color: str
    pallet_spec: str
    pallet_capacity: int

    model_config = {"from_attributes": True}


class WarehouseResponse(BaseModel):
    warehouse_id: int
    warehouse_code: str
    warehouse_name: str

    model_config = {"from_attributes": True}


class LocationResponse(BaseModel):
    location_id: int
    warehouse_id: int
    location_code: str
    zone_code: str
    aisle_code: str
    rack_code: str
    position_code: str

    model_config = {"from_attributes": True}


class ImportBatchResponse(BaseModel):
    batch_id: int
    batch_no: str
    dataset_name: str
    dataset_version: str
    imported_at: datetime
    total_rows: int
    valid_rows: int
    invalid_rows: int
    status: str
    notes: str | None

    model_config = {"from_attributes": True}


class Page(BaseModel):
    total: int
    items: list
