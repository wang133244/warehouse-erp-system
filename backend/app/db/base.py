"""SQLAlchemy DeclarativeBase，所有表模型的基类。"""

from sqlalchemy import MetaData  # 约束命名规则挂在 MetaData 上
from sqlalchemy.orm import DeclarativeBase  # ORM 声明式基类


NAMING_CONVENTION = {  # Alembic 自动生成约束名时用的模板，避免匿名约束难 diff
    "ix": "ix_%(column_0_label)s",  # 普通索引
    "uq": "uq_%(table_name)s_%(column_0_name)s",  # 唯一约束
    "ck": "ck_%(table_name)s_%(constraint_name)s",  # 检查约束
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",  # 外键
    "pk": "pk_%(table_name)s",  # 主键
}  # 命名约定结束


class Base(DeclarativeBase):  # 全部 ORM 模型继承此类
    metadata = MetaData(naming_convention=NAMING_CONVENTION)  # 共享 metadata，迁移 compare 时名称稳定
