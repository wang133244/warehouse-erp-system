"""Pydantic Settings，从 backend/.env 读取数据库、JWT、Redis、DeepSeek 与日志开关。"""

from pathlib import Path  # 定位 backend 目录与 .env 文件

from pydantic_settings import BaseSettings, SettingsConfigDict  # 环境变量/文件配置模型

BACKEND_DIR = Path(__file__).resolve().parents[2]  # 本文件在 app/core，上两级即 backend 根目录


class Settings(BaseSettings):  # 全部运行时配置，可用环境变量覆盖默认值
    app_name: str = "智能ERP仓管系统后端"  # 应用显示名
    app_env: str = "development"  # 运行环境标识
    app_host: str = "127.0.0.1"  # 开发服务器监听地址
    app_port: int = 8000  # 开发服务器端口
    secret_key: str = "change-this-development-secret-key-please"  # JWT 签名密钥，生产必须覆盖
    access_token_expire_minutes: int = 60  # 访问令牌有效分钟数
    database_url: str = "mysql+pymysql://erp_app:replace-me@127.0.0.1:3306/erp_wms?charset=utf8mb4"  # 业务库连接串
    test_database_url: str | None = None  # 测试库连接，未配置则测试自行处理
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"  # 逗号分隔的前端来源
    redis_url: str | None = None  # Redis 地址，空则退回内存缓存
    deepseek_api_key: str = ""  # DeepSeek 密钥，空则助手走关键词规划
    deepseek_base_url: str = "https://api.deepseek.com"  # DeepSeek API 根地址
    deepseek_model: str = "deepseek-chat"  # 默认对话模型名
    log_level: str = "INFO"  # 日志级别
    log_dir: str = ""  # 日志目录，空则用 backend/logs
    log_to_file: bool = True  # 是否同时写滚动文件

    model_config = SettingsConfigDict(  # Pydantic Settings 行为
        env_file=BACKEND_DIR / ".env",  # 从 backend/.env 读取
        env_file_encoding="utf-8",  # 环境文件按 UTF-8 解码
        case_sensitive=False,  # 环境变量名不区分大小写
        extra="ignore",  # 忽略未声明的额外字段，避免升级配置时报错
    )  # Settings 模型配置结束

    @property  # 把逗号串拆成列表给 CORS 中间件
    def cors_origin_list(self) -> list[str]:  # 过滤空段并去掉首尾空白
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]  # 只保留非空来源


# 进程内单例，避免重复读盘；保持原有 __import__("functools").lru_cache 写法。
@__import__("functools").lru_cache  # 进程内缓存 Settings，避免重复读环境
def get_settings() -> Settings:  # 对外获取配置的入口
    return Settings()  # 按 env 与默认值实例化
