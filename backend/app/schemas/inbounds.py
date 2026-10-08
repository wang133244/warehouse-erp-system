"""入库建单与收货确认 DTO。"""

from pydantic import BaseModel, Field  # 导入 Pydantic 基类与字段约束

class InboundItemCreate(BaseModel):  # 入库明细行
    product_id: int; location_id: int; quantity: int = Field(gt=0)  # 商品、库位与入库数量（须大于 0）
class InboundCreate(BaseModel):  # 创建入库单入参
    order_no: str = Field(min_length=1, max_length=64); note: str | None = None; items: list[InboundItemCreate] = Field(min_length=1)  # 单号、备注与至少一行明细

class ReceiveItem(BaseModel):  # 收货确认中的单行实收
    inbound_item_id: int = Field(gt=0)  # 入库明细主键
    received_quantity: int = Field(ge=0)  # 实收数量，允许为 0

class ReceiveConfirm(BaseModel):  # 整单收货确认入参
    note: str | None = Field(default=None, max_length=2000)  # 收货备注
    items: list[ReceiveItem] = Field(default_factory=list)  # 实收明细，默认空列表
