"""调拨申请、审批、执行 DTO。"""

from pydantic import BaseModel, Field, model_validator  # 导入基类、字段约束与模型级校验器


class TransferItemInput(BaseModel):  # 调拨明细行
    product_id: int = Field(gt=0)  # 商品主键
    source_location_id: int = Field(gt=0)  # 源库位
    target_location_id: int = Field(gt=0)  # 目标库位
    quantity: int = Field(gt=0)  # 调拨数量，须大于 0

    @model_validator(mode="after")  # 构造后校验源/目标库位
    def locations_differ(self) -> "TransferItemInput":  # 禁止同库位调拨
        if self.source_location_id == self.target_location_id:  # 源与目标相同则非法
            raise ValueError("源库位和目标库位不能相同")  # 抛出校验错误
        return self  # 校验通过返回自身


class TransferUpsert(BaseModel):  # 新建或更新调拨单入参
    note: str | None = Field(default=None, max_length=2000)  # 调拨备注
    items: list[TransferItemInput] = Field(default_factory=list)  # 调拨明细，默认空列表

    @model_validator(mode="after")  # 构造后检查明细是否重复
    def reject_duplicate_lines(self) -> "TransferUpsert":  # 同一商品+源+目标不得出现两行
        lines = {  # 用集合去重商品/源库位/目标库位组合
            (item.product_id, item.source_location_id, item.target_location_id)  # 单行唯一键
            for item in self.items  # 遍历全部明细
        }  # 去重集合构造结束
        if len(lines) != len(self.items):  # 集合变短说明存在重复行
            raise ValueError("调拨明细中存在重复的商品/源库位/目标库位组合")  # 拒绝重复明细
        return self  # 校验通过返回自身
