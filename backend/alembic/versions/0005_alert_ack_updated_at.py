"""Add missing alert_ack.updated_at for tables created before the column existed.

This migration is additive and guarded. It never removes an existing table,
column, index, or row.
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_alert_ack_updated_at"
down_revision = "0004_ops_hardening"
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


def upgrade() -> None:
    if not _has_column("alert_ack", "updated_at"):
        op.add_column(
            "alert_ack",
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )


def downgrade() -> None:
    """Refuse destructive rollback; restore from a reviewed backup instead."""
    raise NotImplementedError(
        "0005_alert_ack_updated_at 只允许向前迁移；请使用经过评审的备份恢复方案，不自动移除结构。"
    )
