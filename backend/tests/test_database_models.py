from sqlalchemy import CheckConstraint, UniqueConstraint
from backend.app.db.base import Base
from backend.app.db.models import (
    ApprovalTask,
    AuditLog,
    IdempotencyRecord,
    InboundItem,
    InboundOrder,
    OutboundItem,
    OutboundOrder,
    PickingTask,
    Role,
    StockCountItem,
    StockCountOrder,
    StockBalance,
    TransferItem,
    TransferOrder,
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


def test_backend_models_include_warehouse_extensions():
    expected = {
        "stock_count_order",
        "stock_count_item",
        "transfer_order",
        "transfer_item",
        "approval_task",
    }

    assert expected.issubset(Base.metadata.tables)
    assert StockCountOrder.__tablename__ == "stock_count_order"
    assert StockCountItem.__tablename__ == "stock_count_item"
    assert TransferOrder.__tablename__ == "transfer_order"
    assert TransferItem.__tablename__ == "transfer_item"
    assert ApprovalTask.__tablename__ == "approval_task"


def test_warehouse_extension_columns_are_complete():
    expected_columns = {
        StockCountOrder: {
            "stock_count_order_id",
            "order_no",
            "status",
            "created_by",
            "submitted_by",
            "submitted_at",
            "completed_by",
            "completed_at",
            "note",
            "created_at",
            "updated_at",
        },
        StockCountItem: {
            "stock_count_item_id",
            "stock_count_order_id",
            "product_id",
            "location_id",
            "book_quantity",
            "counted_quantity",
            "variance_quantity",
            "created_at",
            "updated_at",
        },
        TransferOrder: {
            "transfer_order_id",
            "order_no",
            "status",
            "transfer_scope",
            "created_by",
            "submitted_by",
            "submitted_at",
            "executed_by",
            "executed_at",
            "note",
            "created_at",
            "updated_at",
        },
        TransferItem: {
            "transfer_item_id",
            "transfer_order_id",
            "product_id",
            "source_location_id",
            "target_location_id",
            "quantity",
            "created_at",
        },
        ApprovalTask: {
            "approval_task_id",
            "business_type",
            "business_id",
            "status",
            "requested_by",
            "requested_at",
            "decided_by",
            "decided_at",
            "comment",
            "created_at",
            "updated_at",
        },
    }

    for model, columns in expected_columns.items():
        assert {column.name for column in model.__table__.columns} == columns


def test_warehouse_extension_constraints_and_indexes_are_named():
    constraint_names = {
        StockCountItem: {"uq_stock_count_item_line", "ck_stock_count_item_counted_nonnegative"},
        TransferItem: {
            "uq_transfer_item_line",
            "ck_transfer_item_quantity_positive",
            "ck_transfer_item_locations_different",
        },
        ApprovalTask: {"uq_approval_business"},
    }
    index_names = {
        StockCountOrder: {"ix_stock_count_order_status_created_at"},
        TransferOrder: {"ix_transfer_order_status_created_at", "ix_transfer_order_scope_status"},
        ApprovalTask: {"ix_approval_task_status_created_at", "ix_approval_task_requested_status"},
    }

    for model, expected_constraints in constraint_names.items():
        actual_unique_constraints = {
            constraint.name
            for constraint in model.__table__.constraints
            if isinstance(constraint, UniqueConstraint)
        }
        actual_check_constraints = {
            constraint.name
            for constraint in model.__table__.constraints
            if isinstance(constraint, CheckConstraint)
        }
        expected_unique_constraints = {
            name for name in expected_constraints if name.startswith("uq_")
        }
        expected_check_constraints = {
            name for name in expected_constraints if name.startswith("ck_")
        }

        assert expected_unique_constraints.issubset(actual_unique_constraints)
        for expected_check_constraint in expected_check_constraints:
            assert any(
                constraint_name == expected_check_constraint
                or constraint_name.endswith(f"_{expected_check_constraint}")
                for constraint_name in actual_check_constraints
            )

    for model, expected_indexes in index_names.items():
        actual_indexes = {index.name for index in model.__table__.indexes}
        assert expected_indexes.issubset(actual_indexes)
