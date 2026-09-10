from pydantic import BaseModel, Field

class OutboundItemCreate(BaseModel):
    product_id: int; quantity: int = Field(gt=0)
class OutboundCreate(BaseModel):
    order_no: str = Field(min_length=1, max_length=64); customer_id: int | None = None; note: str | None = None; items: list[OutboundItemCreate] = Field(min_length=1)
