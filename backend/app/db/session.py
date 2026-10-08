"""按 DATABASE_URL 创建引擎；get_db 给 FastAPI 注入会话。"""

from collections.abc import Generator  # get_db 生成器类型

from sqlalchemy import create_engine  # 创建引擎
from sqlalchemy.orm import Session, sessionmaker  # 会话工厂

from backend.app.core.config import get_settings  # 读取 database_url


settings = get_settings()  # 模块加载时取一次配置
engine = create_engine(  # 进程级引擎，连接池复用
    settings.database_url,  # 业务库 URL
    pool_pre_ping=True,  # 取连接前 ping，避免 MySQL 空闲断开
    pool_recycle=1800,  # 30 分钟回收，降低 wait_timeout 踩坑
)  # create_engine 结束
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)  # 提交后对象仍可读写，适合 API 出参


def get_db() -> Generator[Session, None, None]:  # FastAPI 依赖：请求开始开会话，结束关闭
    db = SessionLocal()  # 新建会话
    try:  # 把会话交给路由
        yield db  # 注入到 Depends(get_db)
    finally:  # 无论成功失败都关闭
        db.close()  # 归还连接到池
