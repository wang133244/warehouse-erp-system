from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class StockBalance(Base):
    __tablename__ = "stock_balance"
    __table_args__ = (UniqueConstraint("product_id", "location_id", name="uq_stock_product_location"),)

    balance_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.product_id"), nullable=False)
    location_id: Mapped[int] = mapped_column(ForeignKey("warehouse_location.location_id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reserved_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class InboundRecord(Base):
    __tablename__ = "inbound_record"

    inbound_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.product_id"), nullable=False)
    location_id: Mapped[int] = mapped_column(ForeignKey("warehouse_location.location_id"), nullable=False)
    staff_id: Mapped[int] = mapped_column(ForeignKey("staff.staff_id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    task: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    source_file: Mapped[str] = mapped_column(String(128), nullable=False)
    source_row: Mapped[int] = mapped_column(Integer, nullable=False)
    source_day: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class OutboundRecord(Base):
    __tablename__ = "outbound_record"

    outbound_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.product_id"), nullable=False)
    location_id: Mapped[int] = mapped_column(ForeignKey("warehouse_location.location_id"), nullable=False)
    staff_id: Mapped[int] = mapped_column(ForeignKey("staff.staff_id"), nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customer.customer_id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    task: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    source_file: Mapped[str] = mapped_column(String(128), nullable=False)
    source_row: Mapped[int] = mapped_column(Integer, nullable=False)
    source_day: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class StockLedger(Base):
    __tablename__ = "stock_ledger"

    ledger_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.product_id"), nullable=False)
    location_id: Mapped[int] = mapped_column(ForeignKey("warehouse_location.location_id"), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    before_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    after_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[int | None] = mapped_column(Integer)
    idempotency_key: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    operator_id: Mapped[int | None] = mapped_column(ForeignKey("staff.staff_id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
