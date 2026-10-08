"""作业单据：入出库、拣货、盘点、调拨、审批；账号角色也在此注册以免重复 metadata。"""

from datetime import datetime  # 时间列类型

from sqlalchemy import (  # 约束、索引与列类型
    CheckConstraint,  # 检查约束，如数量必须为正
    DateTime,  # 日期时间
    ForeignKey,  # 外键
    Index,  # 组合索引
    Integer,  # 整数
    String,  # 字符串
    Text,  # 长文本
    UniqueConstraint,  # 唯一约束
    func,  # 服务器 now()
)  # sqlalchemy 导入结束
from sqlalchemy.orm import Mapped, mapped_column  # 声明式列

from backend.app.db.base import Base  # ORM 基类


class UserAccount(Base):  # 登录账号，可关联 staff
    __tablename__ = "user_account"  # 表名

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 用户主键
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)  # 登录名
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)  # PBKDF2 哈希串
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)  # 显示名
    staff_id: Mapped[int | None] = mapped_column(ForeignKey("staff.staff_id"))  # 可选绑定现场员工
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="1")  # 停用后无法登录
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)  # 创建时间
    updated_at: Mapped[datetime] = mapped_column(  # 资料变更时间
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False  # 自动刷新
    )  # updated_at 结束


class Role(Base):  # RBAC 角色
    __tablename__ = "role"  # 表名

    role_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 角色主键
    role_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)  # 编码：admin/viewer 等
    role_name: Mapped[str] = mapped_column(String(128), nullable=False)  # 中文名
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)  # 创建时间


class UserRole(Base):  # 用户-角色多对多
    __tablename__ = "user_role"  # 表名
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role"),)  # 同一对不重复

    user_id: Mapped[int] = mapped_column(ForeignKey("user_account.user_id"), primary_key=True)  # 用户，联合主键
    role_id: Mapped[int] = mapped_column(ForeignKey("role.role_id"), primary_key=True)  # 角色，联合主键


class UserWarehouseScope(Base):  # 非管理员可操作的仓库范围
    __tablename__ = "user_warehouse_scope"  # 表名
    __table_args__ = (UniqueConstraint("user_id", "warehouse_id", name="uq_user_warehouse_scope"),)  # 同一仓不重复绑定

    user_id: Mapped[int] = mapped_column(ForeignKey("user_account.user_id"), primary_key=True)  # 用户
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouse.warehouse_id"), primary_key=True)  # 仓库


class InboundOrder(Base):  # 入库单头
    __tablename__ = "inbound_order"  # 表名

    inbound_order_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 入库单主键
    order_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)  # 单号
    status: Mapped[str] = mapped_column(  # draft/confirmed 等
        String(32), nullable=False, default="draft", server_default="draft"  # 默认草稿
    )  # status 结束
    created_by: Mapped[int] = mapped_column(ForeignKey("user_account.user_id"), nullable=False)  # 制单人
    confirmed_by: Mapped[int | None] = mapped_column(ForeignKey("user_account.user_id"))  # 确认入库的人
    note: Mapped[str | None] = mapped_column(Text)  # 备注
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)  # 创建时间
    updated_at: Mapped[datetime] = mapped_column(  # 最后修改
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False  # 自动刷新
    )  # updated_at 结束
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime)  # 确认时间


class InboundItem(Base):  # 入库明细：商品+库位+数量
    __tablename__ = "inbound_item"  # 表名

    inbound_item_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 明细主键
    inbound_order_id: Mapped[int] = mapped_column(  # 所属入库单
        ForeignKey("inbound_order.inbound_order_id"), nullable=False  # 外键
    )  # inbound_order_id 结束
    product_id: Mapped[int] = mapped_column(ForeignKey("product.product_id"), nullable=False)  # 商品
    location_id: Mapped[int] = mapped_column(  # 目标库位
        ForeignKey("warehouse_location.location_id"), nullable=False  # 外键
    )  # location_id 结束
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)  # 应收/实收数量
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)  # 创建时间


class OutboundOrder(Base):  # 出库单头
    __tablename__ = "outbound_order"  # 表名

    outbound_order_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 出库单主键
    order_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)  # 单号
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", server_default="draft")  # 默认草稿
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customer.customer_id"))  # 可选客户
    created_by: Mapped[int] = mapped_column(ForeignKey("user_account.user_id"), nullable=False)  # 制单人
    completed_by: Mapped[int | None] = mapped_column(ForeignKey("user_account.user_id"))  # 完成出库的人
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("user_account.user_id"))  # 复核人
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)  # 复核时间
    review_comment: Mapped[str | None] = mapped_column(Text)  # 复核意见
    note: Mapped[str | None] = mapped_column(Text)  # 备注
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)  # 创建时间
    updated_at: Mapped[datetime] = mapped_column(  # 最后修改
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False  # 自动刷新
    )  # updated_at 结束
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)  # 完成时间


class OutboundItem(Base):  # 出库明细：数量、已分配、已拣
    __tablename__ = "outbound_item"  # 表名

    outbound_item_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 明细主键
    outbound_order_id: Mapped[int] = mapped_column(  # 所属出库单
        ForeignKey("outbound_order.outbound_order_id"), nullable=False  # 外键
    )  # outbound_order_id 结束
    product_id: Mapped[int] = mapped_column(ForeignKey("product.product_id"), nullable=False)  # 商品
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)  # 需求数量
    allocated_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")  # 已分配库位数量
    picked_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")  # 已拣数量
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)  # 创建时间


class PickingTask(Base):  # 拣货任务：从某库位拣某商品给某出库明细
    __tablename__ = "picking_task"  # 表名

    picking_task_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 任务主键
    task_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)  # 任务号
    outbound_order_id: Mapped[int] = mapped_column(  # 所属出库单
        ForeignKey("outbound_order.outbound_order_id"), nullable=False  # 外键
    )  # outbound_order_id 结束
    outbound_item_id: Mapped[int] = mapped_column(  # 所属出库明细
        ForeignKey("outbound_item.outbound_item_id"), nullable=False  # 外键
    )  # outbound_item_id 结束
    product_id: Mapped[int] = mapped_column(ForeignKey("product.product_id"), nullable=False)  # 商品
    location_id: Mapped[int] = mapped_column(ForeignKey("warehouse_location.location_id"), nullable=False)  # 拣货库位
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)  # 应拣数量
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="allocated", server_default="allocated")  # 默认已分配
    confirmed_by: Mapped[int | None] = mapped_column(ForeignKey("user_account.user_id"))  # 确认拣货人
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)  # 创建时间
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime)  # 确认时间


class StockCountOrder(Base):  # 盘点单头
    __tablename__ = "stock_count_order"  # 表名
    __table_args__ = (Index("ix_stock_count_order_status_created_at", "status", "created_at"),)  # 按状态+时间列表

    stock_count_order_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 盘点单主键
    order_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)  # 单号
    status: Mapped[str] = mapped_column(  # draft/submitted/completed 等
        String(32), nullable=False, default="draft", server_default="draft"  # 默认草稿
    )  # status 结束
    created_by: Mapped[int] = mapped_column(ForeignKey("user_account.user_id"), nullable=False)  # 制单人
    submitted_by: Mapped[int | None] = mapped_column(ForeignKey("user_account.user_id"))  # 提交人
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime)  # 提交时间
    completed_by: Mapped[int | None] = mapped_column(ForeignKey("user_account.user_id"))  # 过账完成人
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)  # 完成时间
    note: Mapped[str | None] = mapped_column(Text)  # 备注
    created_at: Mapped[datetime] = mapped_column(  # 创建时间
        DateTime, server_default=func.now(), nullable=False  # 服务器默认
    )  # created_at 结束
    updated_at: Mapped[datetime] = mapped_column(  # 最后修改
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False  # 自动刷新
    )  # updated_at 结束


class StockCountItem(Base):  # 盘点明细：账面、实盘、差异
    __tablename__ = "stock_count_item"  # 表名
    __table_args__ = (  # 同行唯一 + 实盘非负
        UniqueConstraint(  # 同一盘点单同一商品库位一行
            "stock_count_order_id",  # 盘点单
            "product_id",  # 商品
            "location_id",  # 库位
            name="uq_stock_count_item_line",  # 约束名
        ),  # UniqueConstraint 结束
        CheckConstraint("counted_quantity >= 0", name="ck_stock_count_item_counted_nonnegative"),  # 实盘不能为负
    )  # table_args 结束

    stock_count_item_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 明细主键
    stock_count_order_id: Mapped[int] = mapped_column(  # 所属盘点单
        ForeignKey("stock_count_order.stock_count_order_id"), nullable=False  # 外键
    )  # stock_count_order_id 结束
    product_id: Mapped[int] = mapped_column(ForeignKey("product.product_id"), nullable=False)  # 商品
    location_id: Mapped[int] = mapped_column(  # 库位
        ForeignKey("warehouse_location.location_id"), nullable=False  # 外键
    )  # location_id 结束
    book_quantity: Mapped[int | None] = mapped_column(Integer)  # 账面数量，提交时快照
    counted_quantity: Mapped[int] = mapped_column(Integer, nullable=False)  # 实盘数量
    variance_quantity: Mapped[int | None] = mapped_column(Integer)  # 差异 = 实盘 - 账面
    created_at: Mapped[datetime] = mapped_column(  # 创建时间
        DateTime, server_default=func.now(), nullable=False  # 服务器默认
    )  # created_at 结束
    updated_at: Mapped[datetime] = mapped_column(  # 最后修改
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False  # 自动刷新
    )  # updated_at 结束


class TransferOrder(Base):  # 调拨单头
    __tablename__ = "transfer_order"  # 表名
    __table_args__ = (  # 列表与范围筛选索引
        Index("ix_transfer_order_status_created_at", "status", "created_at"),  # 状态+时间
        Index("ix_transfer_order_scope_status", "transfer_scope", "status"),  # 范围+状态
    )  # table_args 结束

    transfer_order_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 调拨单主键
    order_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)  # 单号
    status: Mapped[str] = mapped_column(  # draft/submitted/executed 等
        String(32), nullable=False, default="draft", server_default="draft"  # 默认草稿
    )  # status 结束
    transfer_scope: Mapped[str | None] = mapped_column(String(32))  # 仓内/跨仓等范围
    created_by: Mapped[int] = mapped_column(ForeignKey("user_account.user_id"), nullable=False)  # 制单人
    submitted_by: Mapped[int | None] = mapped_column(ForeignKey("user_account.user_id"))  # 提交人
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime)  # 提交时间
    executed_by: Mapped[int | None] = mapped_column(ForeignKey("user_account.user_id"))  # 执行人
    executed_at: Mapped[datetime | None] = mapped_column(DateTime)  # 执行时间
    note: Mapped[str | None] = mapped_column(Text)  # 备注
    created_at: Mapped[datetime] = mapped_column(  # 创建时间
        DateTime, server_default=func.now(), nullable=False  # 服务器默认
    )  # created_at 结束
    updated_at: Mapped[datetime] = mapped_column(  # 最后修改
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False  # 自动刷新
    )  # updated_at 结束


class TransferItem(Base):  # 调拨明细：从源库位到目标库位
    __tablename__ = "transfer_item"  # 表名
    __table_args__ = (  # 同行唯一 + 数量为正 + 源目标不能相同
        UniqueConstraint(  # 同一调拨单同一商品同一路径一行
            "transfer_order_id",  # 调拨单
            "product_id",  # 商品
            "source_location_id",  # 源库位
            "target_location_id",  # 目标库位
            name="uq_transfer_item_line",  # 约束名
        ),  # UniqueConstraint 结束
        CheckConstraint("quantity > 0", name="ck_transfer_item_quantity_positive"),  # 数量必须为正
        CheckConstraint(  # 禁止原地调拨
            "source_location_id <> target_location_id",  # 源目标不同
            name="ck_transfer_item_locations_different",  # 约束名
        ),  # CheckConstraint 结束
    )  # table_args 结束

    transfer_item_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 明细主键
    transfer_order_id: Mapped[int] = mapped_column(  # 所属调拨单
        ForeignKey("transfer_order.transfer_order_id"), nullable=False  # 外键
    )  # transfer_order_id 结束
    product_id: Mapped[int] = mapped_column(ForeignKey("product.product_id"), nullable=False)  # 商品
    source_location_id: Mapped[int] = mapped_column(  # 源库位
        ForeignKey("warehouse_location.location_id"), nullable=False  # 外键
    )  # source_location_id 结束
    target_location_id: Mapped[int] = mapped_column(  # 目标库位
        ForeignKey("warehouse_location.location_id"), nullable=False  # 外键
    )  # target_location_id 结束
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)  # 调拨数量
    created_at: Mapped[datetime] = mapped_column(  # 创建时间
        DateTime, server_default=func.now(), nullable=False  # 服务器默认
    )  # created_at 结束


class ApprovalTask(Base):  # 通用审批任务，按业务类型+业务 ID 唯一
    __tablename__ = "approval_task"  # 表名
    __table_args__ = (  # 业务唯一 + 列表索引
        UniqueConstraint("business_type", "business_id", name="uq_approval_business"),  # 同一单据只挂一条审批
        Index("ix_approval_task_status_created_at", "status", "created_at"),  # 按状态列表
        Index("ix_approval_task_requested_status", "requested_by", "status"),  # 按申请人筛选
    )  # table_args 结束

    approval_task_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 审批主键
    business_type: Mapped[str] = mapped_column(String(32), nullable=False)  # 业务类型：入库/出库等
    business_id: Mapped[int] = mapped_column(Integer, nullable=False)  # 业务单据主键
    status: Mapped[str] = mapped_column(  # 待审、通过或驳回
        String(32), nullable=False, default="pending", server_default="pending"  # 默认待审
    )  # status 结束
    requested_by: Mapped[int] = mapped_column(ForeignKey("user_account.user_id"), nullable=False)  # 申请人
    requested_at: Mapped[datetime] = mapped_column(  # 申请时间
        DateTime, server_default=func.now(), nullable=False  # 服务器默认
    )  # requested_at 结束
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("user_account.user_id"))  # 审批人
    decided_at: Mapped[datetime | None] = mapped_column(DateTime)  # 审批时间
    comment: Mapped[str | None] = mapped_column(Text)  # 审批意见
    created_at: Mapped[datetime] = mapped_column(  # 创建时间
        DateTime, server_default=func.now(), nullable=False  # 服务器默认
    )  # created_at 结束
    updated_at: Mapped[datetime] = mapped_column(  # 最后修改
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False  # 自动刷新
    )  # updated_at 结束
