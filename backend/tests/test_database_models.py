from backend.app.db.base import Base
from backend.app.db.models import (
    AuditLog,
    IdempotencyRecord,
    InboundItem,
    InboundOrder,
    OutboundItem,
    OutboundOrder,
    PickingTask,
    Role,
    StockBalance,
    UserAccount,
)


def test_backend_models_cover_existing_and_new_tables():
    expected_tables = {
        "warehouse",
        "warehouse_location",
        "product",
        "stock_balance",
        "stock_ledger",
        "user_account",
        "role",
        "inbound_order",
        "inbound_item",
        "outbound_order",
        "outbound_item",
        "picking_task",
        "audit_log",
        "idempotency_record",
    }

    assert expected_tables.issubset(Base.metadata.tables)
    assert "reserved_quantity" in StockBalance.__table__.columns
    assert UserAccount.__tablename__ == "user_account"
    assert Role.__tablename__ == "role"
    assert InboundOrder.__tablename__ == "inbound_order"
    assert InboundItem.__tablename__ == "inbound_item"
    assert OutboundOrder.__tablename__ == "outbound_order"
    assert OutboundItem.__tablename__ == "outbound_item"
    assert PickingTask.__tablename__ == "picking_task"
    assert AuditLog.__tablename__ == "audit_log"
    assert IdempotencyRecord.__tablename__ == "idempotency_record"
