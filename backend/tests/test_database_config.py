from backend.app.core.config import Settings


def test_database_url_can_be_overridden(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")

    settings = Settings(_env_file=None)

    assert settings.database_url == "sqlite+pysqlite:///:memory:"


def test_default_database_url_does_not_embed_root_password(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    settings = Settings(_env_file=None)

    assert "root" not in settings.database_url.lower()
    assert "@" in settings.database_url
