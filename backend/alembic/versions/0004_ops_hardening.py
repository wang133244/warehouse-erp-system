"""Add catalog active flags and stock freeze quantity.

This migration is additive and guarded so interrupted reruns do not duplicate
schema objects. It never removes an existing table, column, index, or row.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql as mysql_dialect


def mysql_unsigned_integer():
    """Match the imported baseline schema's INT UNSIGNED primary and foreign keys."""
    return sa.Integer().with_variant(mysql_dialect.INTEGER(unsigned=True), "mysql")


revision = "0004_ops_hardening"
down_revision = "0003_followup_ops"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(column["name"] == column_name for column in _inspector().get_columns(table_name))


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def upgrade() -> None:
    _add_column_if_missing(
        "product",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
    )
    _add_column_if_missing(
        "warehouse_location",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
    )
    _add_column_if_missing(
        "stock_balance",
        sa.Column("frozen_quantity", mysql_unsigned_integer(), nullable=False, server_default=sa.text("0")),
    )


def downgrade() -> None:
    """Refuse destructive rollback; restore from a reviewed backup instead."""
    raise NotImplementedError(
        "0004_ops_hardening 只允许向前迁移；请使用经过评审的备份恢复方案，不自动移除结构。"
    )
