from pydantic import BaseModel, Field

class InboundItemCreate(BaseModel):
    product_id: int; location_id: int; quantity: int = Field(gt=0)
class InboundCreate(BaseModel):
    order_no: str = Field(min_length=1, max_length=64); note: str | None = None; items: list[InboundItemCreate] = Field(min_length=1)
