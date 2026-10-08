"""主数据：商品、仓库、库位、客户、员工、导入批次。"""

from datetime import datetime  # 时间列的 Python 类型

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func  # 列类型、外键与服务器时间
from sqlalchemy.orm import Mapped, mapped_column, relationship  # 声明式映射与关系

from backend.app.db.base import Base  # 共享 DeclarativeBase


class Warehouse(Base):  # 仓库主数据
    __tablename__ = "warehouse"  # 表名

    warehouse_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 仓库主键
    warehouse_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)  # 仓库编码，全局唯一
    warehouse_name: Mapped[str] = mapped_column(String(128), nullable=False)  # 仓库显示名
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)  # 创建时间由数据库填写

    locations: Mapped[list["WarehouseLocation"]] = relationship(back_populates="warehouse")  # 下属库位


class WarehouseLocation(Base):  # 库位：区-巷-架-位
    __tablename__ = "warehouse_location"  # 表名

    location_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 库位主键
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouse.warehouse_id"), nullable=False)  # 所属仓库
    location_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)  # 库位编码，全局唯一
    zone_code: Mapped[str] = mapped_column(String(8), nullable=False)  # 库区
    aisle_code: Mapped[str] = mapped_column(String(16), nullable=False)  # 巷道
    rack_code: Mapped[str] = mapped_column(String(16), nullable=False)  # 货架
    position_code: Mapped[str] = mapped_column(String(8), nullable=False)  # 货位
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="1")  # 是否启用
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)  # 创建时间

    warehouse: Mapped[Warehouse] = relationship(back_populates="locations")  # 反向指向仓库


class Product(Base):  # 商品 SKU
    __tablename__ = "product"  # 表名

    product_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 商品主键
    sku_code: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)  # 对外 SKU，查询助手用
    source_product_code: Mapped[str] = mapped_column(String(64), nullable=False)  # 来源系统商品码
    brand: Mapped[str] = mapped_column(String(128), nullable=False)  # 品牌
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)  # 品名
    category: Mapped[str] = mapped_column(String(128), nullable=False)  # 品类
    size: Mapped[str] = mapped_column(String(128), nullable=False)  # 规格尺寸
    function_feature: Mapped[str] = mapped_column(String(128), nullable=False)  # 功能特征
    color: Mapped[str] = mapped_column(String(64), nullable=False)  # 颜色
    pallet_spec: Mapped[str] = mapped_column(String(64), nullable=False)  # 托盘规格
    pallet_capacity: Mapped[int] = mapped_column(Integer, nullable=False)  # 每托数量
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="1")  # 是否在售/在用
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)  # 创建时间
    updated_at: Mapped[datetime] = mapped_column(  # 更新时间，ORM 写操作会刷新
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False  # 库默认与 onupdate
    )  # updated_at 结束


class Staff(Base):  # 现场员工，可关联登录账号
    __tablename__ = "staff"  # 表名

    staff_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 员工主键
    staff_name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)  # 员工姓名，当前按名唯一
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)  # 创建时间


class Customer(Base):  # 出库客户
    __tablename__ = "customer"  # 表名

    customer_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 客户主键
    customer_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)  # 客户编码
    customer_name: Mapped[str | None] = mapped_column(String(128))  # 客户名称，可空
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)  # 创建时间


class DataImportBatch(Base):  # 历史 Excel/CSV 导入批次，只读追溯
    __tablename__ = "data_import_batch"  # 表名

    batch_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 批次主键
    batch_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)  # 批次号
    dataset_name: Mapped[str] = mapped_column(String(128), nullable=False)  # 数据集名称
    dataset_version: Mapped[str] = mapped_column(String(32), nullable=False)  # 数据集版本
    imported_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)  # 导入时间
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False)  # 总行数
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False)  # 有效行
    invalid_rows: Mapped[int] = mapped_column(Integer, nullable=False)  # 无效行
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # 导入状态
    notes: Mapped[str | None] = mapped_column(Text)  # 备注
