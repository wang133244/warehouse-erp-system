"""ORM 表能建、关键字段存在。"""

from sqlalchemy import CheckConstraint, UniqueConstraint  # from sqlalchemy import C
from backend.app.db.base import Base  # from backend.app.db.base
from backend.app.models import (  # from backend.app.models 
    ApprovalTask,  # ApprovalTask,
    AuditLog,  # AuditLog,
    IdempotencyRecord,  # IdempotencyRecord,
    InboundItem,  # InboundItem,
    InboundOrder,  # InboundOrder,
    OutboundItem,  # OutboundItem,
    OutboundOrder,  # OutboundOrder,
    PickingTask,  # PickingTask,
    Role,  # Role,
    StockCountItem,  # StockCountItem,
    StockCountOrder,  # StockCountOrder,
    StockBalance,  # StockBalance,
    TransferItem,  # TransferItem,
    TransferOrder,  # TransferOrder,
    UserAccount,  # UserAccount,
)  # )


def test_backend_models_cover_existing_and_new_tables():  # def test_backend_models_
    expected_tables = {  # expected_tables = {
        "warehouse",  # 'warehouse',
        "warehouse_location",  # 'warehouse_location',
        "product",  # 'product',
        "stock_balance",  # 'stock_balance',
        "stock_ledger",  # 'stock_ledger',
        "user_account",  # 'user_account',
        "role",  # 'role',
        "inbound_order",  # 'inbound_order',
        "inbound_item",  # 'inbound_item',
        "outbound_order",  # 'outbound_order',
        "outbound_item",  # 'outbound_item',
        "picking_task",  # 'picking_task',
        "audit_log",  # 'audit_log',
        "idempotency_record",  # 'idempotency_record',
    }  # }

    assert expected_tables.issubset(Base.metadata.tables)  # assert expected_tables.i
    assert "reserved_quantity" in StockBalance.__table__.columns  # assert 'reserved_quantit
    assert UserAccount.__tablename__ == "user_account"  # assert UserAccount.__tab
    assert Role.__tablename__ == "role"  # assert Role.__tablename_
    assert InboundOrder.__tablename__ == "inbound_order"  # assert InboundOrder.__ta
    assert InboundItem.__tablename__ == "inbound_item"  # assert InboundItem.__tab
    assert OutboundOrder.__tablename__ == "outbound_order"  # assert OutboundOrder.__t
    assert OutboundItem.__tablename__ == "outbound_item"  # assert OutboundItem.__ta
    assert PickingTask.__tablename__ == "picking_task"  # assert PickingTask.__tab
    assert AuditLog.__tablename__ == "audit_log"  # assert AuditLog.__tablen
    assert IdempotencyRecord.__tablename__ == "idempotency_record"  # assert IdempotencyRecord


def test_backend_models_include_warehouse_extensions():  # def test_backend_models_
    expected = {  # expected = {
        "stock_count_order",  # 'stock_count_order',
        "stock_count_item",  # 'stock_count_item',
        "transfer_order",  # 'transfer_order',
        "transfer_item",  # 'transfer_item',
        "approval_task",  # 'approval_task',
    }  # }

    assert expected.issubset(Base.metadata.tables)  # assert expected.issubset
    assert StockCountOrder.__tablename__ == "stock_count_order"  # assert StockCountOrder._
    assert StockCountItem.__tablename__ == "stock_count_item"  # assert StockCountItem.__
    assert TransferOrder.__tablename__ == "transfer_order"  # assert TransferOrder.__t
    assert TransferItem.__tablename__ == "transfer_item"  # assert TransferItem.__ta
    assert ApprovalTask.__tablename__ == "approval_task"  # assert ApprovalTask.__ta


def test_warehouse_extension_columns_are_complete():  # def test_warehouse_exten
    expected_columns = {  # expected_columns = {
        StockCountOrder: {  # StockCountOrder: {
            "stock_count_order_id",  # 'stock_count_order_id',
            "order_no",  # 'order_no',
            "status",  # 'status',
            "created_by",  # 'created_by',
            "submitted_by",  # 'submitted_by',
            "submitted_at",  # 'submitted_at',
            "completed_by",  # 'completed_by',
            "completed_at",  # 'completed_at',
            "note",  # 'note',
            "created_at",  # 'created_at',
            "updated_at",  # 'updated_at',
        },  # },
        StockCountItem: {  # StockCountItem: {
            "stock_count_item_id",  # 'stock_count_item_id',
            "stock_count_order_id",  # 'stock_count_order_id',
            "product_id",  # 'product_id',
            "location_id",  # 'location_id',
            "book_quantity",  # 'book_quantity',
            "counted_quantity",  # 'counted_quantity',
            "variance_quantity",  # 'variance_quantity',
            "created_at",  # 'created_at',
            "updated_at",  # 'updated_at',
        },  # },
        TransferOrder: {  # TransferOrder: {
            "transfer_order_id",  # 'transfer_order_id',
            "order_no",  # 'order_no',
            "status",  # 'status',
            "transfer_scope",  # 'transfer_scope',
            "created_by",  # 'created_by',
            "submitted_by",  # 'submitted_by',
            "submitted_at",  # 'submitted_at',
            "executed_by",  # 'executed_by',
            "executed_at",  # 'executed_at',
            "note",  # 'note',
            "created_at",  # 'created_at',
            "updated_at",  # 'updated_at',
        },  # },
        TransferItem: {  # TransferItem: {
            "transfer_item_id",  # 'transfer_item_id',
            "transfer_order_id",  # 'transfer_order_id',
            "product_id",  # 'product_id',
            "source_location_id",  # 'source_location_id',
            "target_location_id",  # 'target_location_id',
            "quantity",  # 'quantity',
            "created_at",  # 'created_at',
        },  # },
        ApprovalTask: {  # ApprovalTask: {
            "approval_task_id",  # 'approval_task_id',
            "business_type",  # 'business_type',
            "business_id",  # 'business_id',
            "status",  # 'status',
            "requested_by",  # 'requested_by',
            "requested_at",  # 'requested_at',
            "decided_by",  # 'decided_by',
            "decided_at",  # 'decided_at',
            "comment",  # 'comment',
            "created_at",  # 'created_at',
            "updated_at",  # 'updated_at',
        },  # },
    }  # }

    for model, columns in expected_columns.items():  # for model, columns in ex
        assert {column.name for column in model.__table__.columns} == columns  # assert {column.name for 


def test_warehouse_extension_constraints_and_indexes_are_named():  # def test_warehouse_exten
    constraint_names = {  # constraint_names = {
        StockCountItem: {"uq_stock_count_item_line", "ck_stock_count_item_counted_nonnegative"},  # StockCountItem: {'uq_sto
        TransferItem: {  # TransferItem: {
            "uq_transfer_item_line",  # 'uq_transfer_item_line',
            "ck_transfer_item_quantity_positive",  # 'ck_transfer_item_quanti
            "ck_transfer_item_locations_different",  # 'ck_transfer_item_locati
        },  # },
        ApprovalTask: {"uq_approval_business"},  # ApprovalTask: {'uq_appro
    }  # }
    index_names = {  # index_names = {
        StockCountOrder: {"ix_stock_count_order_status_created_at"},  # StockCountOrder: {'ix_st
        TransferOrder: {"ix_transfer_order_status_created_at", "ix_transfer_order_scope_status"},  # TransferOrder: {'ix_tran
        ApprovalTask: {"ix_approval_task_status_created_at", "ix_approval_task_requested_status"},  # ApprovalTask: {'ix_appro
    }  # }

    for model, expected_constraints in constraint_names.items():  # for model, expected_cons
        actual_unique_constraints = {  # actual_unique_constraint
            constraint.name  # constraint.name
            for constraint in model.__table__.constraints  # for constraint in model.
            if isinstance(constraint, UniqueConstraint)  # if isinstance(constraint
        }  # }
        actual_check_constraints = {  # actual_check_constraints
            constraint.name  # constraint.name
            for constraint in model.__table__.constraints  # for constraint in model.
            if isinstance(constraint, CheckConstraint)  # if isinstance(constraint
        }  # }
        expected_unique_constraints = {  # expected_unique_constrai
            name for name in expected_constraints if name.startswith("uq_")  # name for name in expecte
        }  # }
        expected_check_constraints = {  # expected_check_constrain
            name for name in expected_constraints if name.startswith("ck_")  # name for name in expecte
        }  # }

        assert expected_unique_constraints.issubset(actual_unique_constraints)  # assert expected_unique_c
        for expected_check_constraint in expected_check_constraints:  # for expected_check_const
            assert any(  # assert any(
                constraint_name == expected_check_constraint  # constraint_name == expec
                or constraint_name.endswith(f"_{expected_check_constraint}")  # or constraint_name.endsw
                for constraint_name in actual_check_constraints  # for constraint_name in a
            )  # )

    for model, expected_indexes in index_names.items():  # for model, expected_inde
        actual_indexes = {index.name for index in model.__table__.indexes}  # actual_indexes = {index.
        assert expected_indexes.issubset(actual_indexes)  # assert expected_indexes.
