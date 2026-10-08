"""Pydantic DTO 包；常用认证 schema 在此再导出。"""

from backend.app.schemas.auth import CurrentUserResponse, LoginRequest, TokenResponse  # 再导出常用认证 DTO，便于短路径 import

__all__ = ["CurrentUserResponse", "LoginRequest", "TokenResponse"]  # 限定包对外公开的三个认证模型名
