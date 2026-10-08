"""出库建单、分配、复核、完成 DTO。"""

from pydantic import BaseModel, Field  # 导入 Pydantic 基类与字段约束

class OutboundItemCreate(BaseModel):  # 出库明细行
    product_id: int; quantity: int = Field(gt=0)  # 商品与出库数量（须大于 0）
class OutboundCreate(BaseModel):  # 创建出库单入参
    order_no: str = Field(min_length=1, max_length=64); customer_id: int | None = None; note: str | None = None; items: list[OutboundItemCreate] = Field(min_length=1)  # 单号、客户、备注与至少一行明细

class OutboundReview(BaseModel):  # 出库复核意见
    comment: str | None = Field(default=None, max_length=2000)  # 复核备注，可选
