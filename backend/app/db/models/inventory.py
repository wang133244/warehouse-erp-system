"""库存事实（余额、流水）与历史只读收发货记录。"""

from datetime import datetime  # 时间列类型

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func  # 列、外键、唯一约束
from sqlalchemy.orm import Mapped, mapped_column  # 声明式列

from backend.app.db.base import Base  # ORM 基类


class StockBalance(Base):  # 商品在某库位上的当前数量，是库存事实源
    __tablename__ = "stock_balance"  # 表名
    __table_args__ = (UniqueConstraint("product_id", "location_id", name="uq_stock_product_location"),)  # 同一商品同一库位只有一行

    balance_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 余额主键
    product_id: Mapped[int] = mapped_column(ForeignKey("product.product_id"), nullable=False)  # 商品
    location_id: Mapped[int] = mapped_column(ForeignKey("warehouse_location.location_id"), nullable=False)  # 库位
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)  # 在库数量
    reserved_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")  # 已预留待拣
    frozen_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")  # 冻结不可用
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)  # 创建时间
    updated_at: Mapped[datetime] = mapped_column(  # 每次库存变更刷新
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False  # 服务器默认与 onupdate
    )  # updated_at 结束


class InboundRecord(Base):  # 导入的历史入库流水，只读，不参与当前余额计算
    __tablename__ = "inbound_record"  # 表名

    inbound_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 历史入库主键
    product_id: Mapped[int] = mapped_column(ForeignKey("product.product_id"), nullable=False)  # 商品
    location_id: Mapped[int] = mapped_column(ForeignKey("warehouse_location.location_id"), nullable=False)  # 库位
    staff_id: Mapped[int] = mapped_column(ForeignKey("staff.staff_id"), nullable=False)  # 操作员工
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)  # 数量
    task: Mapped[str] = mapped_column(String(64), nullable=False)  # 来源任务名
    action: Mapped[str] = mapped_column(String(64), nullable=False)  # 动作描述
    source_file: Mapped[str] = mapped_column(String(128), nullable=False)  # 导入文件名
    source_row: Mapped[int] = mapped_column(Integer, nullable=False)  # 源文件行号
    source_day: Mapped[int] = mapped_column(Integer, nullable=False)  # 源数据日期序号
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)  # 写入时间


class OutboundRecord(Base):  # 导入的历史出库流水，只读
    __tablename__ = "outbound_record"  # 表名

    outbound_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 历史出库主键
    product_id: Mapped[int] = mapped_column(ForeignKey("product.product_id"), nullable=False)  # 商品
    location_id: Mapped[int] = mapped_column(ForeignKey("warehouse_location.location_id"), nullable=False)  # 库位
    staff_id: Mapped[int] = mapped_column(ForeignKey("staff.staff_id"), nullable=False)  # 操作员工
    customer_id: Mapped[int] = mapped_column(ForeignKey("customer.customer_id"), nullable=False)  # 客户
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)  # 数量
    task: Mapped[str] = mapped_column(String(64), nullable=False)  # 来源任务名
    action: Mapped[str] = mapped_column(String(64), nullable=False)  # 动作描述
    source_file: Mapped[str] = mapped_column(String(128), nullable=False)  # 导入文件名
    source_row: Mapped[int] = mapped_column(Integer, nullable=False)  # 源文件行号
    source_day: Mapped[int] = mapped_column(Integer, nullable=False)  # 源数据日期序号
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)  # 写入时间


class StockLedger(Base):  # 库存流水：每次余额变更记一笔，可按幂等键去重
    __tablename__ = "stock_ledger"  # 表名

    ledger_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 流水主键
    product_id: Mapped[int] = mapped_column(ForeignKey("product.product_id"), nullable=False)  # 商品
    location_id: Mapped[int] = mapped_column(ForeignKey("warehouse_location.location_id"), nullable=False)  # 库位
    transaction_type: Mapped[str] = mapped_column(String(32), nullable=False)  # 入/出/盘点/调拨等类型
    quantity_delta: Mapped[int] = mapped_column(Integer, nullable=False)  # 数量变化，可正可负
    before_quantity: Mapped[int] = mapped_column(Integer, nullable=False)  # 变更前数量
    after_quantity: Mapped[int] = mapped_column(Integer, nullable=False)  # 变更后数量
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)  # 来源单据类型
    source_id: Mapped[int | None] = mapped_column(Integer)  # 来源单据主键，可空
    idempotency_key: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)  # 防重复记账
    operator_id: Mapped[int | None] = mapped_column(ForeignKey("staff.staff_id"))  # 现场操作员工，可空
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)  # 记账时间
