"""库存余额、流水、可用量 DTO。"""

from pydantic import BaseModel, Field  # 导入 Pydantic 基类与字段约束（Field 保留与原文件一致）

class InventoryBalance(BaseModel):  # 库存余额行
    balance_id: int; product_id: int; location_id: int; quantity: int; reserved_quantity: int; available_quantity: int  # 主键、商品、库位、在库、预留与可用量

class Availability(BaseModel):  # 商品维度可用量汇总
    product_id: int; quantity: int; reserved_quantity: int; available_quantity: int  # 商品、在库合计、预留合计与可用合计
