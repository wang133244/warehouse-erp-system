"""盘点建单、实盘、提交 DTO。"""

from pydantic import BaseModel, Field, model_validator  # 导入基类、字段约束与模型级校验器


class StockCountItemInput(BaseModel):  # 盘点明细行
    product_id: int = Field(gt=0)  # 商品主键
    location_id: int = Field(gt=0)  # 库位主键
    counted_quantity: int = Field(ge=0)  # 实盘数量，允许为 0


class StockCountUpsert(BaseModel):  # 新建或更新盘点单入参
    note: str | None = Field(default=None, max_length=2000)  # 盘点备注
    items: list[StockCountItemInput] = Field(default_factory=list)  # 实盘明细，默认空列表

    @model_validator(mode="after")  # 构造后检查明细是否重复
    def reject_duplicate_lines(self) -> "StockCountUpsert":  # 同一商品+库位不得出现两行
        lines = {(item.product_id, item.location_id) for item in self.items}  # 用集合去重商品/库位组合
        if len(lines) != len(self.items):  # 集合变短说明存在重复行
            raise ValueError("盘点明细中存在重复的商品/库位组合")  # 拒绝重复明细
        return self  # 校验通过返回自身


class StockCountListQuery(BaseModel):  # 盘点列表查询参数
    page: int = Field(default=1, ge=1)  # 页码，从 1 起
    page_size: int = Field(default=20, ge=1, le=100)  # 每页条数，1–100
    status: str | None = Field(default=None, max_length=32)  # 按状态筛选
    order_no: str | None = Field(default=None, max_length=64)  # 按单号筛选
