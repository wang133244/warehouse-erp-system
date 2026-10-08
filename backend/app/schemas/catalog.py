"""商品、仓库、库位的入参出参。"""

from datetime import datetime  # 导入批次导入时间字段类型
from pydantic import BaseModel  # 导入 Pydantic 基类


class ProductResponse(BaseModel):  # 商品查询/详情出参
    product_id: int  # 商品主键
    sku_code: str  # 内部 SKU 编码
    source_product_code: str  # 来源商品编码
    brand: str  # 品牌
    product_name: str  # 商品名称
    category: str  # 品类
    size: str  # 规格尺寸
    function_feature: str  # 功能特征
    color: str  # 颜色
    pallet_spec: str  # 托盘规格
    pallet_capacity: int  # 托盘容量
    is_active: bool = True  # 是否启用，默认启用

    model_config = {"from_attributes": True}  # 允许从 ORM 属性填充


class WarehouseResponse(BaseModel):  # 仓库出参
    warehouse_id: int  # 仓库主键
    warehouse_code: str  # 仓库编码
    warehouse_name: str  # 仓库名称

    model_config = {"from_attributes": True}  # 允许从 ORM 属性填充


class LocationResponse(BaseModel):  # 库位出参
    location_id: int  # 库位主键
    warehouse_id: int  # 所属仓库 ID
    location_code: str  # 库位编码
    zone_code: str  # 库区编码
    aisle_code: str  # 巷道编码
    rack_code: str  # 货架编码
    position_code: str  # 货位编码
    is_active: bool = True  # 是否启用，默认启用

    model_config = {"from_attributes": True}  # 允许从 ORM 属性填充


class ImportBatchResponse(BaseModel):  # 商品 CSV 导入批次出参
    batch_id: int  # 批次主键
    batch_no: str  # 批次号
    dataset_name: str  # 数据集名称
    dataset_version: str  # 数据集版本
    imported_at: datetime  # 导入时间
    total_rows: int  # 总行数
    valid_rows: int  # 有效行数
    invalid_rows: int  # 无效行数
    status: str  # 批次状态
    notes: str | None  # 备注，可为空

    model_config = {"from_attributes": True}  # 允许从 ORM 属性填充


class Page(BaseModel):  # 通用分页外壳
    total: int  # 总条数
    items: list  # 当前页数据列表
