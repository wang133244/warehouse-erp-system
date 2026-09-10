from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class Warehouse(Base):
    __tablename__ = "warehouse"

    warehouse_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    warehouse_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    warehouse_name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    locations: Mapped[list["WarehouseLocation"]] = relationship(back_populates="warehouse")


class WarehouseLocation(Base):
    __tablename__ = "warehouse_location"

    location_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouse.warehouse_id"), nullable=False)
    location_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    zone_code: Mapped[str] = mapped_column(String(8), nullable=False)
    aisle_code: Mapped[str] = mapped_column(String(16), nullable=False)
    rack_code: Mapped[str] = mapped_column(String(16), nullable=False)
    position_code: Mapped[str] = mapped_column(String(8), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    warehouse: Mapped[Warehouse] = relationship(back_populates="locations")


class Product(Base):
    __tablename__ = "product"

    product_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku_code: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    source_product_code: Mapped[str] = mapped_column(String(64), nullable=False)
    brand: Mapped[str] = mapped_column(String(128), nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False)
    size: Mapped[str] = mapped_column(String(128), nullable=False)
    function_feature: Mapped[str] = mapped_column(String(128), nullable=False)
    color: Mapped[str] = mapped_column(String(64), nullable=False)
    pallet_spec: Mapped[str] = mapped_column(String(64), nullable=False)
    pallet_capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Staff(Base):
    __tablename__ = "staff"

    staff_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    staff_name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class Customer(Base):
    __tablename__ = "customer"

    customer_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    customer_name: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class DataImportBatch(Base):
    __tablename__ = "data_import_batch"

    batch_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    dataset_name: Mapped[str] = mapped_column(String(128), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(32), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    invalid_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
