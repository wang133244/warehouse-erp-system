from pathlib import Path
from importlib.util import module_from_spec, spec_from_file_location

import sqlalchemy as sa


def test_initial_backend_migration_is_additive_only():
    migration = Path(__file__).parents[1] / "alembic" / "versions" / "0001_add_backend_core.py"

    assert migration.exists()
    source = migration.read_text(encoding="utf-8").lower()
    assert "add_column(\"stock_balance\"" in source
    assert "create_table(\"user_account\"" in source
    assert "drop_table" not in source
    assert "drop_column" not in source


def test_initial_backend_migration_uses_mysql_unsigned_integers():
    migration = Path(__file__).parents[1] / "alembic" / "versions" / "0001_add_backend_core.py"

    source = migration.read_text(encoding="utf-8").lower()
    assert "integer(unsigned=true)" in source


def test_mysql_unsigned_integer_helper_is_not_recursive():
    from importlib.util import module_from_spec, spec_from_file_location

    migration = Path(__file__).parents[1] / "alembic" / "versions" / "0001_add_backend_core.py"
    spec = spec_from_file_location("add_backend_core_migration", migration)
    module = module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)

    column_type = module.mysql_unsigned_integer()

    assert column_type is not None


def test_create_table_if_missing_passes_all_arguments(monkeypatch):
    migration = Path(__file__).parents[1] / "alembic" / "versions" / "0001_add_backend_core.py"
    spec = spec_from_file_location("add_backend_core_migration", migration)
    module = module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)

    calls = []
    monkeypatch.setattr(module.op, "create_table", lambda *args, **kwargs: calls.append(args))
    monkeypatch.setattr(module, "_has_table", lambda table_name: False)
    first = sa.Column("id", module.mysql_unsigned_integer(), primary_key=True)
    second = sa.Column("name", sa.String(length=32), nullable=False)
    constraint = sa.UniqueConstraint("name", name="uq_probe_name")

    module._create_table_if_missing("probe", first, second, constraint)

    assert calls == [("probe", first, second, constraint)]
