"""Add stock count, transfer, and approval tables.

This migration is additive and guarded so interrupted reruns do not duplicate
schema objects. It never removes an existing table, column, index, or row.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql as mysql_dialect


def mysql_unsigned_integer():
    """Match the imported baseline schema's INT UNSIGNED primary and foreign keys."""
    return sa.Integer().with_variant(mysql_dialect.INTEGER(unsigned=True), "mysql")


revision = "0002_stock_count_transfer_approval"
down_revision = "0001_add_backend_core"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _has_index(table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in _inspector().get_indexes(table_name))


def _create_table_if_missing(table_name: str, *args: object) -> None:
    if not _has_table(table_name):
        op.create_table(table_name, *args)


def _create_index_if_missing(
    index_name: str,
    table_name: str,
    columns: list[str],
) -> None:
    if _has_table(table_name) and not _has_index(table_name, index_name):
        op.create_index(index_name, table_name, columns)


def upgrade() -> None:
    _create_table_if_missing(
        "stock_count_order",
        sa.Column(
            "stock_count_order_id", mysql_unsigned_integer(), primary_key=True, autoincrement=True
        ),
        sa.Column("order_no", sa.String(length=64), nullable=False),
        sa.Column(
            "status", sa.String(length=32), nullable=False, server_default=sa.text("'draft'")
        ),
        sa.Column("created_by", mysql_unsigned_integer(), nullable=False),
        sa.Column("submitted_by", mysql_unsigned_integer(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("completed_by", mysql_unsigned_integer(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("order_no", name="uq_stock_count_order_order_no"),
        sa.ForeignKeyConstraint(
            ["created_by"], ["user_account.user_id"], name="fk_stock_count_order_created_by"
        ),
        sa.ForeignKeyConstraint(
            ["submitted_by"], ["user_account.user_id"], name="fk_stock_count_order_submitted_by"
        ),
        sa.ForeignKeyConstraint(
            ["completed_by"], ["user_account.user_id"], name="fk_stock_count_order_completed_by"
        ),
    )
    _create_index_if_missing(
        "ix_stock_count_order_status_created_at",
        "stock_count_order",
        ["status", "created_at"],
    )

    _create_table_if_missing(
        "stock_count_item",
        sa.Column(
            "stock_count_item_id", mysql_unsigned_integer(), primary_key=True, autoincrement=True
        ),
        sa.Column("stock_count_order_id", mysql_unsigned_integer(), nullable=False),
        sa.Column("product_id", mysql_unsigned_integer(), nullable=False),
        sa.Column("location_id", mysql_unsigned_integer(), nullable=False),
        sa.Column("book_quantity", sa.Integer(), nullable=True),
        sa.Column("counted_quantity", sa.Integer(), nullable=False),
        sa.Column("variance_quantity", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "stock_count_order_id",
            "product_id",
            "location_id",
            name="uq_stock_count_item_line",
        ),
        sa.CheckConstraint(
            "counted_quantity >= 0", name="ck_stock_count_item_counted_nonnegative"
        ),
        sa.ForeignKeyConstraint(
            ["stock_count_order_id"],
            ["stock_count_order.stock_count_order_id"],
            name="fk_stock_count_item_order",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["product.product_id"], name="fk_stock_count_item_product"
        ),
        sa.ForeignKeyConstraint(
            ["location_id"], ["warehouse_location.location_id"], name="fk_stock_count_item_location"
        ),
    )

    _create_table_if_missing(
        "transfer_order",
        sa.Column(
            "transfer_order_id", mysql_unsigned_integer(), primary_key=True, autoincrement=True
        ),
        sa.Column("order_no", sa.String(length=64), nullable=False),
        sa.Column(
            "status", sa.String(length=32), nullable=False, server_default=sa.text("'draft'")
        ),
        sa.Column("transfer_scope", sa.String(length=32), nullable=True),
        sa.Column("created_by", mysql_unsigned_integer(), nullable=False),
        sa.Column("submitted_by", mysql_unsigned_integer(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("executed_by", mysql_unsigned_integer(), nullable=True),
        sa.Column("executed_at", sa.DateTime(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("order_no", name="uq_transfer_order_order_no"),
        sa.ForeignKeyConstraint(
            ["created_by"], ["user_account.user_id"], name="fk_transfer_order_created_by"
        ),
        sa.ForeignKeyConstraint(
            ["submitted_by"], ["user_account.user_id"], name="fk_transfer_order_submitted_by"
        ),
        sa.ForeignKeyConstraint(
            ["executed_by"], ["user_account.user_id"], name="fk_transfer_order_executed_by"
        ),
    )
    _create_index_if_missing(
        "ix_transfer_order_status_created_at",
        "transfer_order",
        ["status", "created_at"],
    )
    _create_index_if_missing(
        "ix_transfer_order_scope_status",
        "transfer_order",
        ["transfer_scope", "status"],
    )

    _create_table_if_missing(
        "transfer_item",
        sa.Column(
            "transfer_item_id", mysql_unsigned_integer(), primary_key=True, autoincrement=True
        ),
        sa.Column("transfer_order_id", mysql_unsigned_integer(), nullable=False),
        sa.Column("product_id", mysql_unsigned_integer(), nullable=False),
        sa.Column("source_location_id", mysql_unsigned_integer(), nullable=False),
        sa.Column("target_location_id", mysql_unsigned_integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "transfer_order_id",
            "product_id",
            "source_location_id",
            "target_location_id",
            name="uq_transfer_item_line",
        ),
        sa.CheckConstraint("quantity > 0", name="ck_transfer_item_quantity_positive"),
        sa.CheckConstraint(
            "source_location_id <> target_location_id",
            name="ck_transfer_item_locations_different",
        ),
        sa.ForeignKeyConstraint(
            ["transfer_order_id"],
            ["transfer_order.transfer_order_id"],
            name="fk_transfer_item_order",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["product.product_id"], name="fk_transfer_item_product"
        ),
        sa.ForeignKeyConstraint(
            ["source_location_id"],
            ["warehouse_location.location_id"],
            name="fk_transfer_item_source_location",
        ),
        sa.ForeignKeyConstraint(
            ["target_location_id"],
            ["warehouse_location.location_id"],
            name="fk_transfer_item_target_location",
        ),
    )

    _create_table_if_missing(
        "approval_task",
        sa.Column(
            "approval_task_id", mysql_unsigned_integer(), primary_key=True, autoincrement=True
        ),
        sa.Column("business_type", sa.String(length=32), nullable=False),
        sa.Column("business_id", mysql_unsigned_integer(), nullable=False),
        sa.Column(
            "status", sa.String(length=32), nullable=False, server_default=sa.text("'pending'")
        ),
        sa.Column("requested_by", mysql_unsigned_integer(), nullable=False),
        sa.Column("requested_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("decided_by", mysql_unsigned_integer(), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("business_type", "business_id", name="uq_approval_business"),
        sa.ForeignKeyConstraint(
            ["requested_by"], ["user_account.user_id"], name="fk_approval_task_requested_by"
        ),
        sa.ForeignKeyConstraint(
            ["decided_by"], ["user_account.user_id"], name="fk_approval_task_decided_by"
        ),
    )
    _create_index_if_missing(
        "ix_approval_task_status_created_at",
        "approval_task",
        ["status", "created_at"],
    )
    _create_index_if_missing(
        "ix_approval_task_requested_status",
        "approval_task",
        ["requested_by", "status"],
    )


def downgrade() -> None:
    """Refuse destructive rollback; restore from a reviewed backup instead."""
    raise NotImplementedError(
        "0002_stock_count_transfer_approval 只允许向前迁移；请使用经过评审的备份恢复方案，不自动移除结构。"
    )
