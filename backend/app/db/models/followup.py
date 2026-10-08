"""助手会话消息与预警确认。"""

from datetime import datetime  # 时间列类型

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func  # 列类型与唯一约束
from sqlalchemy.orm import Mapped, mapped_column  # 声明式列

from backend.app.db.base import Base  # ORM 基类


class AlertAck(Base):  # 某条库存余额预警的确认记录，每个余额最多一条
    __tablename__ = "alert_ack"  # 表名
    __table_args__ = (UniqueConstraint("balance_id", name="uq_alert_ack_balance"),)  # 同一余额只确认一次

    alert_ack_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 确认主键
    balance_id: Mapped[int] = mapped_column(ForeignKey("stock_balance.balance_id"), nullable=False)  # 对应库存余额
    product_id: Mapped[int] = mapped_column(ForeignKey("product.product_id"), nullable=False)  # 冗余商品，便于列表
    location_id: Mapped[int] = mapped_column(ForeignKey("warehouse_location.location_id"), nullable=False)  # 冗余库位
    acked_by: Mapped[int] = mapped_column(ForeignKey("user_account.user_id"), nullable=False)  # 确认人
    note: Mapped[str | None] = mapped_column(Text)  # 确认说明
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)  # 首次确认时间
    updated_at: Mapped[datetime] = mapped_column(  # 再次更新备注时刷新
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False  # 自动刷新
    )  # updated_at 结束


class AgentSession(Base):  # 助手对话会话
    __tablename__ = "agent_session"  # 表名

    session_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 会话主键
    user_id: Mapped[int] = mapped_column(ForeignKey("user_account.user_id"), nullable=False)  # 所属用户
    title: Mapped[str] = mapped_column(String(128), nullable=False, default="新会话")  # 侧边栏标题
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)  # 创建时间
    updated_at: Mapped[datetime] = mapped_column(  # 有新消息时刷新，用于排序
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False  # 自动刷新
    )  # updated_at 结束


class AgentMessage(Base):  # 会话内一条消息（用户或助手）
    __tablename__ = "agent_message"  # 表名

    message_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 消息主键
    session_id: Mapped[int] = mapped_column(ForeignKey("agent_session.session_id"), nullable=False)  # 所属会话
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # 消息角色：用户或助手
    content: Mapped[str] = mapped_column(Text, nullable=False)  # 正文
    tool_calls: Mapped[list | None] = mapped_column(JSON)  # 本轮调用过的白名单工具
    draft: Mapped[dict | None] = mapped_column(JSON)  # 若生成草稿则存结构化草稿
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)  # 写入时间
