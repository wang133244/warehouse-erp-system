"""业务异常 AppError，由中间件收成稳定 JSON 错误信封。"""

from dataclasses import dataclass, field  # 用数据类承载错误字段
from typing import Any  # details 的宽松类型


@dataclass  # 自动生成初始化，便于 raise AppError(...)
class AppError(Exception):  # 领域错误，最终变成 {code, message, details}
    """A domain error rendered by the API's stable error envelope."""

    code: str  # 稳定机器码，前端可按码分支
    message: str  # 给人看的说明
    status_code: int = 400  # 默认客户端错误
    details: dict[str, Any] = field(default_factory=dict)  # 附加上下文，缺省空字典
