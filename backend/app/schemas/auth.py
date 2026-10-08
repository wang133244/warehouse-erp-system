"""登录、令牌、当前用户的请求响应模型。"""

from pydantic import BaseModel, Field  # 导入 Pydantic 基类与字段约束


class LoginRequest(BaseModel):  # 登录请求体
    username: str = Field(min_length=1, max_length=64)  # 登录用户名，1–64 字符
    password: str = Field(min_length=1, max_length=256)  # 登录密码，1–256 字符


class TokenResponse(BaseModel):  # 登录成功返回的令牌
    access_token: str  # JWT 访问令牌
    token_type: str = "bearer"  # 令牌类型固定为 bearer
    expires_in: int  # 令牌有效期（秒）


class CurrentUserResponse(BaseModel):  # 当前登录用户资料
    user_id: int  # 用户主键
    username: str  # 登录名
    display_name: str  # 显示名
    roles: list[str]  # 角色编码列表
