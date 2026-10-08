"""数据库 URL 与会话工厂。"""

from backend.app.core.config import Settings  # from backend.app.core.co


def test_database_url_can_be_overridden(monkeypatch):  # def test_database_url_ca
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")  # monkeypatch.setenv('DATA

    settings = Settings(_env_file=None)  # settings = Settings(_env

    assert settings.database_url == "sqlite+pysqlite:///:memory:"  # assert settings.database


def test_default_database_url_does_not_embed_root_password(monkeypatch):  # def test_default_databas
    monkeypatch.delenv("DATABASE_URL", raising=False)  # monkeypatch.delenv('DATA

    settings = Settings(_env_file=None)  # settings = Settings(_env

    assert "root" not in settings.database_url.lower()  # assert 'root' not in set
    assert "@" in settings.database_url  # assert '@' in settings.d
