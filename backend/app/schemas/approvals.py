"""审批同意/驳回 DTO。"""

from pydantic import BaseModel, Field, model_validator  # 导入基类、字段约束与模型级校验器


class ApprovalDecision(BaseModel):  # 审批同意或驳回时的意见体
    comment: str | None = Field(default=None, max_length=500)  # 审批意见，可选，最长 500

    @model_validator(mode="after")  # 模型构造完成后规范化意见
    def normalize_comment(self) -> "ApprovalDecision":  # 去掉空白，空串视为未填
        self.comment = self.comment.strip() if self.comment else None  # 有内容则 strip，否则置 None
        return self  # 返回规范化后的自身
