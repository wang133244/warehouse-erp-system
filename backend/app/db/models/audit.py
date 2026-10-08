"""操作审计与写操作幂等记录。"""

from datetime import datetime  # 时间列类型

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func  # 列类型与唯一约束
from sqlalchemy.orm import Mapped, mapped_column  # 声明式列

from backend.app.db.base import Base  # ORM 基类


class AuditLog(Base):  # 关键写操作审计，按 request_id 可与访问日志对齐
    __tablename__ = "audit_log"  # 表名

    audit_log_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 审计主键
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)  # 请求关联 ID
    user_id: Mapped[int | None] = mapped_column(ForeignKey("user_account.user_id"))  # 操作者，系统任务可空
    action: Mapped[str] = mapped_column(String(64), nullable=False)  # 动作名
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)  # 实体类型
    entity_id: Mapped[str | None] = mapped_column(String(64))  # 实体主键，字符串以兼容复合 ID
    before_state: Mapped[dict | None] = mapped_column(JSON)  # 变更前快照
    after_state: Mapped[dict | None] = mapped_column(JSON)  # 变更后快照
    quantity_before: Mapped[int | None] = mapped_column(Integer)  # 库存相关操作的变更前数量
    quantity_after: Mapped[int | None] = mapped_column(Integer)  # 变更后数量
    client_ip: Mapped[str | None] = mapped_column(String(64))  # 客户端 IP
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)  # 记录时间


class IdempotencyRecord(Base):  # 用户级幂等：同一 key 重复提交返回首次结果
    __tablename__ = "idempotency_record"  # 表名
    __table_args__ = (UniqueConstraint("user_id", "idempotency_key", name="uq_idempotency_user_key"),)  # 用户+键唯一

    idempotency_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 幂等记录主键
    user_id: Mapped[int] = mapped_column(ForeignKey("user_account.user_id"), nullable=False)  # 提交用户
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)  # 客户端幂等键
    request_method: Mapped[str] = mapped_column(String(16), nullable=False)  # HTTP 方法
    request_path: Mapped[str] = mapped_column(String(255), nullable=False)  # 路径
    response_status: Mapped[int | None] = mapped_column(Integer)  # 首次响应状态，处理中可空
    response_body: Mapped[dict | None] = mapped_column(JSON)  # 首次响应体，供重放
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)  # 创建时间
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)  # 过期后可重新占用该键
