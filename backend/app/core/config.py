from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "智能ERP仓管系统后端"
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    secret_key: str = "change-this-development-secret-key-please"
    access_token_expire_minutes: int = 60
    database_url: str = "mysql+pymysql://erp_app:replace-me@127.0.0.1:3306/erp_wms?charset=utf8mb4"
    test_database_url: str | None = None
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    redis_url: str | None = None

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@__import__("functools").lru_cache
def get_settings() -> Settings:
    return Settings()
