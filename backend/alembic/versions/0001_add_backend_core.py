"""Add backend tables and the reservation quantity column.

This migration assumes the ten imported baseline tables from database/schema.sql
already exist. It is deliberately additive: it never removes a table, column,
or existing row. Existing data is preserved, and the new reservation column is
backfilled with zero.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql as mysql_dialect


def mysql_unsigned_integer():
    """Match the imported baseline schema's INT UNSIGNED primary and foreign keys."""
    return sa.Integer().with_variant(mysql_dialect.INTEGER(unsigned=True), "mysql")


revision = "0001_add_backend_core"
down_revision = None
branch_labels = None
depends_on = None

BASELINE_TABLES = {
    "warehouse",
    "warehouse_location",
    "product",
    "staff",
    "customer",
    "stock_balance",
    "inbound_record",
    "outbound_record",
    "data_import_batch",
    "stock_ledger",
}


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in _inspector().get_columns(table_name))


def _create_table_if_missing(table_name: str, *args: object) -> None:
    if not _has_table(table_name):
        op.create_table(table_name, *args)


def upgrade() -> None:
    inspector = _inspector()
    existing_tables = set(inspector.get_table_names())
    missing_baseline = sorted(BASELINE_TABLES - existing_tables)
    if missing_baseline:
        raise RuntimeError(
            "基础导入表不存在，已停止增量迁移；请先确认 database/schema.sql 的导入状态："
            + ", ".join(missing_baseline)
        )

    if not _has_column("stock_balance", "reserved_quantity"):
        op.add_column("stock_balance",
            sa.Column(
                "reserved_quantity",
                mysql_unsigned_integer(),
                nullable=False,
                server_default=sa.text("0"),
            ),
        )

    # Equivalent Alembic primitive: op.create_table("user_account", ...); guarded for safe reruns.
    _create_table_if_missing(
        "user_account",
        sa.Column("user_id", mysql_unsigned_integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("staff_id", mysql_unsigned_integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("username", name="uq_user_account_username"),
        sa.ForeignKeyConstraint(["staff_id"], ["staff.staff_id"], name="fk_user_account_staff"),
    )

    _create_table_if_missing(
        "role",
        sa.Column("role_id", mysql_unsigned_integer(), primary_key=True, autoincrement=True),
        sa.Column("role_code", sa.String(length=64), nullable=False),
        sa.Column("role_name", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("role_code", name="uq_role_role_code"),
    )

    _create_table_if_missing(
        "user_role",
        sa.Column("user_id", mysql_unsigned_integer(), nullable=False),
        sa.Column("role_id", mysql_unsigned_integer(), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_role"),
        sa.ForeignKeyConstraint(["user_id"], ["user_account.user_id"], name="fk_user_role_user"),
        sa.ForeignKeyConstraint(["role_id"], ["role.role_id"], name="fk_user_role_role"),
    )

    _create_table_if_missing(
        "user_warehouse_scope",
        sa.Column("user_id", mysql_unsigned_integer(), nullable=False),
        sa.Column("warehouse_id", mysql_unsigned_integer(), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "warehouse_id"),
        sa.UniqueConstraint("user_id", "warehouse_id", name="uq_user_warehouse_scope"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user_account.user_id"], name="fk_user_warehouse_scope_user"
        ),
        sa.ForeignKeyConstraint(
            ["warehouse_id"], ["warehouse.warehouse_id"], name="fk_user_warehouse_scope_warehouse"
        ),
    )

    _create_table_if_missing(
        "inbound_order",
        sa.Column("inbound_order_id", mysql_unsigned_integer(), primary_key=True, autoincrement=True),
        sa.Column("order_no", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("created_by", mysql_unsigned_integer(), nullable=False),
        sa.Column("confirmed_by", mysql_unsigned_integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("order_no", name="uq_inbound_order_order_no"),
        sa.ForeignKeyConstraint(
            ["created_by"], ["user_account.user_id"], name="fk_inbound_order_created_by"
        ),
        sa.ForeignKeyConstraint(
            ["confirmed_by"], ["user_account.user_id"], name="fk_inbound_order_confirmed_by"
        ),
    )

    _create_table_if_missing(
        "inbound_item",
        sa.Column("inbound_item_id", mysql_unsigned_integer(), primary_key=True, autoincrement=True),
        sa.Column("inbound_order_id", mysql_unsigned_integer(), nullable=False),
        sa.Column("product_id", mysql_unsigned_integer(), nullable=False),
        sa.Column("location_id", mysql_unsigned_integer(), nullable=False),
        sa.Column("quantity", mysql_unsigned_integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["inbound_order_id"], ["inbound_order.inbound_order_id"], name="fk_inbound_item_order"
        ),
        sa.ForeignKeyConstraint(["product_id"], ["product.product_id"], name="fk_inbound_item_product"),
        sa.ForeignKeyConstraint(
            ["location_id"], ["warehouse_location.location_id"], name="fk_inbound_item_location"
        ),
    )

    _create_table_if_missing(
        "outbound_order",
        sa.Column("outbound_order_id", mysql_unsigned_integer(), primary_key=True, autoincrement=True),
        sa.Column("order_no", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("customer_id", mysql_unsigned_integer(), nullable=True),
        sa.Column("created_by", mysql_unsigned_integer(), nullable=False),
        sa.Column("completed_by", mysql_unsigned_integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("order_no", name="uq_outbound_order_order_no"),
        sa.ForeignKeyConstraint(
            ["customer_id"], ["customer.customer_id"], name="fk_outbound_order_customer"
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["user_account.user_id"], name="fk_outbound_order_created_by"
        ),
        sa.ForeignKeyConstraint(
            ["completed_by"], ["user_account.user_id"], name="fk_outbound_order_completed_by"
        ),
    )

    _create_table_if_missing(
        "outbound_item",
        sa.Column("outbound_item_id", mysql_unsigned_integer(), primary_key=True, autoincrement=True),
        sa.Column("outbound_order_id", mysql_unsigned_integer(), nullable=False),
        sa.Column("product_id", mysql_unsigned_integer(), nullable=False),
        sa.Column("quantity", mysql_unsigned_integer(), nullable=False),
        sa.Column("allocated_quantity", mysql_unsigned_integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("picked_quantity", mysql_unsigned_integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["outbound_order_id"], ["outbound_order.outbound_order_id"], name="fk_outbound_item_order"
        ),
        sa.ForeignKeyConstraint(["product_id"], ["product.product_id"], name="fk_outbound_item_product"),
    )

    _create_table_if_missing(
        "picking_task",
        sa.Column("picking_task_id", mysql_unsigned_integer(), primary_key=True, autoincrement=True),
        sa.Column("task_no", sa.String(length=64), nullable=False),
        sa.Column("outbound_order_id", mysql_unsigned_integer(), nullable=False),
        sa.Column("outbound_item_id", mysql_unsigned_integer(), nullable=False),
        sa.Column("product_id", mysql_unsigned_integer(), nullable=False),
        sa.Column("location_id", mysql_unsigned_integer(), nullable=False),
        sa.Column("quantity", mysql_unsigned_integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'allocated'")),
        sa.Column("confirmed_by", mysql_unsigned_integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("task_no", name="uq_picking_task_task_no"),
        sa.ForeignKeyConstraint(
            ["outbound_order_id"], ["outbound_order.outbound_order_id"], name="fk_picking_task_order"
        ),
        sa.ForeignKeyConstraint(
            ["outbound_item_id"], ["outbound_item.outbound_item_id"], name="fk_picking_task_item"
        ),
        sa.ForeignKeyConstraint(["product_id"], ["product.product_id"], name="fk_picking_task_product"),
        sa.ForeignKeyConstraint(
            ["location_id"], ["warehouse_location.location_id"], name="fk_picking_task_location"
        ),
        sa.ForeignKeyConstraint(
            ["confirmed_by"], ["user_account.user_id"], name="fk_picking_task_confirmed_by"
        ),
    )

    _create_table_if_missing(
        "audit_log",
        sa.Column("audit_log_id", mysql_unsigned_integer(), primary_key=True, autoincrement=True),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", mysql_unsigned_integer(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("before_state", sa.JSON(), nullable=True),
        sa.Column("after_state", sa.JSON(), nullable=True),
        sa.Column("quantity_before", mysql_unsigned_integer(), nullable=True),
        sa.Column("quantity_after", mysql_unsigned_integer(), nullable=True),
        sa.Column("client_ip", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["user_account.user_id"], name="fk_audit_log_user"),
    )

    _create_table_if_missing(
        "idempotency_record",
        sa.Column("idempotency_id", mysql_unsigned_integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", mysql_unsigned_integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("request_method", sa.String(length=16), nullable=False),
        sa.Column("request_path", sa.String(length=255), nullable=False),
        sa.Column("response_status", mysql_unsigned_integer(), nullable=True),
        sa.Column("response_body", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_idempotency_user_key"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user_account.user_id"], name="fk_idempotency_record_user"
        ),
    )


def downgrade() -> None:
    """Refuse destructive rollback; restore from a reviewed backup instead."""
    raise NotImplementedError(
        "0001_add_backend_core 只允许向前迁移；请使用经过评审的备份恢复方案，不自动移除结构。"
    )




