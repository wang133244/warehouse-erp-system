"""数据库包：Base 与模型注册。"""

from backend.app.db.base import Base  # 导出 DeclarativeBase，迁移与模型共用
from backend.app.db import models  # noqa: F401  # 导入即注册全部表到 metadata

__all__ = ["Base"]  # 对外只显式导出 Base
