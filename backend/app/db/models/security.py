"""Compatibility exports for security models.

The canonical ORM definitions live in ``operations.py`` so each table is
registered exactly once in SQLAlchemy metadata.
"""

from backend.app.db.models.operations import Role, UserAccount, UserRole, UserWarehouseScope  # 从作业模块再导出，避免重复注册表

__all__ = ["Role", "UserAccount", "UserRole", "UserWarehouseScope"]  # 兼容旧导入路径
