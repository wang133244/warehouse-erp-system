"""Alembic environment for the backend's additive migrations."""

from logging.config import fileConfig  # 按 alembic.ini 配日志
from pathlib import Path  # 定位 backend 与仓库根
import sys  # 把仓库根加入 PYTHONPATH

from alembic import context  # 迁移上下文
from sqlalchemy import engine_from_config, pool  # 在线模式建引擎，用 NullPool

BACKEND_DIR = Path(__file__).resolve().parents[1]  # alembic/ 的上一级即 backend
PROJECT_ROOT = BACKEND_DIR.parent  # 仓库根，import backend.app 需要
if str(PROJECT_ROOT) not in sys.path:  # 尚未加入
    sys.path.insert(0, str(PROJECT_ROOT))  # 保证能 import 模型

from backend.app.core.config import get_settings  # noqa: E402  # 读取 DATABASE_URL
from backend.app.db.base import Base  # noqa: E402  # 目标 metadata
from backend.app.db import models  # noqa: F401,E402  # 导入即注册全部表


config = context.config  # 取出 Alembic 运行时配置对象
if config.config_file_name is not None:  # 有 ini 才配日志
    fileConfig(config.config_file_name)  # 避免覆盖应用日志时仍可用 alembic 自己的

settings = get_settings()  # 从环境/.env 取 URL
# Keep the URL in environment/configuration rather than source control. Alembic's
# ConfigParser interpolation requires percent signs to be escaped here.
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))  # 百分号转义给 ConfigParser
target_metadata = Base.metadata  # autogenerate / compare 用的元数据


def run_migrations_offline() -> None:  # 离线：只生成 SQL，不连库
    """Generate SQL without opening a database connection."""
    url = config.get_main_option("sqlalchemy.url")  # 已写入的 URL
    context.configure(  # 离线配置
        url=url,  # 用于渲染方言 SQL
        target_metadata=target_metadata,  # 模型 metadata
        literal_binds=True,  # 把绑定值写进 SQL
        dialect_opts={"paramstyle": "named"},  # 命名参数风格
        compare_type=True,  # 比较列类型
        compare_server_default=True,  # 比较服务器默认值
    )  # configure 结束

    with context.begin_transaction():  # 事务块（离线仅为脚本边界）
        context.run_migrations()  # 跑版本脚本


def run_migrations_online() -> None:  # 在线：连库执行
    """Run migrations using the configured SQLAlchemy engine."""
    connectable = engine_from_config(  # 按 ini 的 sqlalchemy. 前缀建引擎
        config.get_section(config.config_ini_section, {}),  # alembic 段
        prefix="sqlalchemy.",  # 只取 sqlalchemy.*
        poolclass=pool.NullPool,  # 迁移进程不持连接池
    )  # engine_from_config 结束

    with connectable.connect() as connection:  # 一条连接跑完
        context.configure(  # 在线配置
            connection=connection,  # 使用该连接
            target_metadata=target_metadata,  # 模型 metadata
            compare_type=True,  # 比较类型
            compare_server_default=True,  # 比较默认值
        )  # configure 结束

        with context.begin_transaction():  # 事务内执行，失败回滚
            context.run_migrations()  # 跑版本脚本


if context.is_offline_mode():  # alembic -x 或 --sql 离线
    run_migrations_offline()  # 只出 SQL
else:  # 默认在线
    run_migrations_online()  # 连库升级
