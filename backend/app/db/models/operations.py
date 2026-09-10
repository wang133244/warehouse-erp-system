from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class UserAccount(Base):
    __tablename__ = "user_account"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    staff_id: Mapped[int | None] = mapped_column(ForeignKey("staff.staff_id"))
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Role(Base):
    __tablename__ = "role"

    role_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    role_name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class UserRole(Base):
    __tablename__ = "user_role"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role"),)

    user_id: Mapped[int] = mapped_column(ForeignKey("user_account.user_id"), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("role.role_id"), primary_key=True)


class UserWarehouseScope(Base):
    __tablename__ = "user_warehouse_scope"
    __table_args__ = (UniqueConstraint("user_id", "warehouse_id", name="uq_user_warehouse_scope"),)

    user_id: Mapped[int] = mapped_column(ForeignKey("user_account.user_id"), primary_key=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouse.warehouse_id"), primary_key=True)


class InboundOrder(Base):
    __tablename__ = "inbound_order"

    inbound_order_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", server_default="draft")
    created_by: Mapped[int] = mapped_column(ForeignKey("user_account.user_id"), nullable=False)
    confirmed_by: Mapped[int | None] = mapped_column(ForeignKey("user_account.user_id"))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime)


class InboundItem(Base):
    __tablename__ = "inbound_item"

    inbound_item_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    inbound_order_id: Mapped[int] = mapped_column(
        ForeignKey("inbound_order.inbound_order_id"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(ForeignKey("product.product_id"), nullable=False)
    location_id: Mapped[int] = mapped_column(ForeignKey("warehouse_location.location_id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class OutboundOrder(Base):
    __tablename__ = "outbound_order"

    outbound_order_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", server_default="draft")
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customer.customer_id"))
    created_by: Mapped[int] = mapped_column(ForeignKey("user_account.user_id"), nullable=False)
    completed_by: Mapped[int | None] = mapped_column(ForeignKey("user_account.user_id"))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)


class OutboundItem(Base):
    __tablename__ = "outbound_item"

    outbound_item_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    outbound_order_id: Mapped[int] = mapped_column(
        ForeignKey("outbound_order.outbound_order_id"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(ForeignKey("product.product_id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    allocated_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    picked_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class PickingTask(Base):
    __tablename__ = "picking_task"

    picking_task_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    outbound_order_id: Mapped[int] = mapped_column(
        ForeignKey("outbound_order.outbound_order_id"), nullable=False
    )
    outbound_item_id: Mapped[int] = mapped_column(
        ForeignKey("outbound_item.outbound_item_id"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(ForeignKey("product.product_id"), nullable=False)
    location_id: Mapped[int] = mapped_column(ForeignKey("warehouse_location.location_id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="allocated", server_default="allocated")
    confirmed_by: Mapped[int | None] = mapped_column(ForeignKey("user_account.user_id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime)
