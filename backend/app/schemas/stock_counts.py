from pydantic import BaseModel, Field, model_validator


class StockCountItemInput(BaseModel):
    product_id: int = Field(gt=0)
    location_id: int = Field(gt=0)
    counted_quantity: int = Field(ge=0)


class StockCountUpsert(BaseModel):
    note: str | None = Field(default=None, max_length=2000)
    items: list[StockCountItemInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def reject_duplicate_lines(self) -> "StockCountUpsert":
        lines = {(item.product_id, item.location_id) for item in self.items}
        if len(lines) != len(self.items):
            raise ValueError("盘点明细中存在重复的商品/库位组合")
        return self


class StockCountListQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    status: str | None = Field(default=None, max_length=32)
    order_no: str | None = Field(default=None, max_length=64)
