"""Add outbound review fields and follow-up operations tables.

This migration is additive and guarded so interrupted reruns do not duplicate
schema objects. It never removes an existing table, column, index, or row.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql as mysql_dialect


def mysql_unsigned_integer():
    """Match the imported baseline schema's INT UNSIGNED primary and foreign keys."""
    return sa.Integer().with_variant(mysql_dialect.INTEGER(unsigned=True), "mysql")


revision = "0003_followup_ops"
down_revision = "0002_stock_count_transfer_approval"
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


def _create_table_if_missing(table_name: str, *args: object) -> None:
    if not _has_table(table_name):
        op.create_table(table_name, *args)


def upgrade() -> None:
    _add_column_if_missing(
        "outbound_order",
        sa.Column("reviewed_by", mysql_unsigned_integer(), nullable=True),
    )
    _add_column_if_missing(
        "outbound_order",
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
    )
    _add_column_if_missing(
        "outbound_order",
        sa.Column("review_comment", sa.Text(), nullable=True),
    )

    _create_table_if_missing(
        "alert_ack",
        sa.Column("alert_ack_id", mysql_unsigned_integer(), primary_key=True, autoincrement=True),
        sa.Column("balance_id", mysql_unsigned_integer(), nullable=False),
        sa.Column("product_id", mysql_unsigned_integer(), nullable=False),
        sa.Column("location_id", mysql_unsigned_integer(), nullable=False),
        sa.Column("acked_by", mysql_unsigned_integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("balance_id", name="uq_alert_ack_balance"),
        sa.ForeignKeyConstraint(["balance_id"], ["stock_balance.balance_id"], name="fk_alert_ack_balance"),
        sa.ForeignKeyConstraint(["product_id"], ["product.product_id"], name="fk_alert_ack_product"),
        sa.ForeignKeyConstraint(["location_id"], ["warehouse_location.location_id"], name="fk_alert_ack_location"),
        sa.ForeignKeyConstraint(["acked_by"], ["user_account.user_id"], name="fk_alert_ack_user"),
    )
    _create_table_if_missing(
        "agent_session",
        sa.Column("session_id", mysql_unsigned_integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", mysql_unsigned_integer(), nullable=False),
        sa.Column("title", sa.String(length=128), nullable=False, server_default=sa.text("'新会话'")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["user_account.user_id"], name="fk_agent_session_user"),
    )
    _create_table_if_missing(
        "agent_message",
        sa.Column("message_id", mysql_unsigned_integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", mysql_unsigned_integer(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tool_calls", sa.JSON(), nullable=True),
        sa.Column("draft", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["session_id"], ["agent_session.session_id"], name="fk_agent_message_session"),
    )


def downgrade() -> None:
    """Refuse destructive rollback; restore from a reviewed backup instead."""
    raise NotImplementedError(
        "0003_followup_ops 只允许向前迁移；请使用经过评审的备份恢复方案，不自动移除结构。"
    )
