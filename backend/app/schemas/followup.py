"""助手会话、预警确认、用户管理 DTO。"""

from pydantic import BaseModel, Field  # 导入 Pydantic 基类与字段约束


class UserCreate(BaseModel):  # 新建用户入参
    username: str = Field(min_length=1, max_length=64)  # 登录名
    password: str = Field(min_length=6, max_length=128)  # 初始密码，至少 6 位
    display_name: str = Field(min_length=1, max_length=128)  # 显示名
    roles: list[str] = Field(min_length=1)  # 角色编码，至少一项
    warehouse_ids: list[int] = Field(default_factory=list)  # 授权仓库 ID，默认空列表
    is_active: bool = True  # 是否启用，默认启用


class UserUpdate(BaseModel):  # 更新用户入参，未传字段不改
    display_name: str | None = Field(default=None, min_length=1, max_length=128)  # 新显示名
    password: str | None = Field(default=None, min_length=6, max_length=128)  # 新密码
    roles: list[str] | None = None  # 新角色列表
    warehouse_ids: list[int] | None = None  # 新授权仓库
    is_active: bool | None = None  # 启用状态


class ProductCreate(BaseModel):  # 新建商品入参
    sku_code: str = Field(min_length=1, max_length=160)  # 内部 SKU
    source_product_code: str = Field(min_length=1, max_length=64)  # 来源商品编码
    brand: str = Field(min_length=1, max_length=128)  # 品牌
    product_name: str = Field(min_length=1, max_length=255)  # 商品名称
    category: str = Field(min_length=1, max_length=128)  # 品类
    size: str = Field(min_length=1, max_length=128)  # 规格尺寸
    function_feature: str = Field(min_length=1, max_length=128)  # 功能特征
    color: str = Field(min_length=1, max_length=64)  # 颜色
    pallet_spec: str = Field(min_length=1, max_length=64)  # 托盘规格
    pallet_capacity: int = Field(gt=0)  # 托盘容量，须大于 0
    is_active: bool = True  # 是否启用，默认启用


class ProductUpdate(BaseModel):  # 部分更新商品入参
    source_product_code: str | None = Field(default=None, min_length=1, max_length=64)  # 来源商品编码
    brand: str | None = Field(default=None, min_length=1, max_length=128)  # 品牌
    product_name: str | None = Field(default=None, min_length=1, max_length=255)  # 商品名称
    category: str | None = Field(default=None, min_length=1, max_length=128)  # 品类
    size: str | None = Field(default=None, min_length=1, max_length=128)  # 规格尺寸
    function_feature: str | None = Field(default=None, min_length=1, max_length=128)  # 功能特征
    color: str | None = Field(default=None, min_length=1, max_length=64)  # 颜色
    pallet_spec: str | None = Field(default=None, min_length=1, max_length=64)  # 托盘规格
    pallet_capacity: int | None = Field(default=None, gt=0)  # 托盘容量
    is_active: bool | None = None  # 启用状态


class LocationCreate(BaseModel):  # 新建库位入参
    warehouse_id: int  # 所属仓库
    location_code: str = Field(min_length=1, max_length=32)  # 库位编码
    zone_code: str = Field(min_length=1, max_length=8)  # 库区
    aisle_code: str = Field(min_length=1, max_length=16)  # 巷道
    rack_code: str = Field(min_length=1, max_length=16)  # 货架
    position_code: str = Field(min_length=1, max_length=8)  # 货位
    is_active: bool = True  # 是否启用，默认启用


class LocationUpdate(BaseModel):  # 部分更新库位入参
    zone_code: str | None = Field(default=None, min_length=1, max_length=8)  # 库区
    aisle_code: str | None = Field(default=None, min_length=1, max_length=16)  # 巷道
    rack_code: str | None = Field(default=None, min_length=1, max_length=16)  # 货架
    position_code: str | None = Field(default=None, min_length=1, max_length=8)  # 货位
    is_active: bool | None = None  # 启用状态


class WarehouseCreate(BaseModel):  # 新建仓库入参
    warehouse_code: str = Field(min_length=1, max_length=32)  # 仓库编码
    warehouse_name: str = Field(min_length=1, max_length=128)  # 仓库名称


class ProductCsvImport(BaseModel):  # 商品 CSV 文本导入入参
    content: str = Field(min_length=1)  # CSV 文件内容
    filename: str | None = Field(default="products.csv", max_length=128)  # 原始文件名，默认 products.csv


class AgentMessageCreate(BaseModel):  # 助手会话发消息入参
    content: str = Field(min_length=1, max_length=2000)  # 用户消息正文


class AlertAckCreate(BaseModel):  # 预警确认入参
    note: str | None = Field(default=None, max_length=500)  # 确认备注，可选
