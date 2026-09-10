import ast
from pathlib import Path
from importlib.util import module_from_spec, spec_from_file_location

import sqlalchemy as sa


EXTENSION_MIGRATION = (
    Path(__file__).parents[1] / "alembic" / "versions" / "0002_stock_count_transfer_approval.py"
)


def _first_argument_strings(tree: ast.Module, function_name: str) -> set[str]:
    arguments = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == function_name
            and node.args
        ):
            argument = node.args[0]
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                arguments.add(argument.value)
    return arguments


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


def test_extension_migration_is_additive_and_depends_on_core():
    assert EXTENSION_MIGRATION.exists()
    source = EXTENSION_MIGRATION.read_text(encoding="utf-8").lower()

    assert 'revision = "0002_stock_count_transfer_approval"' in source
    assert 'down_revision = "0001_add_backend_core"' in source
    assert "create_table" in source
    assert "drop_table" not in source
    assert "drop_column" not in source
    assert "drop_index" not in source


def test_extension_migration_creates_guarded_tables_and_named_indexes():
    assert EXTENSION_MIGRATION.exists()
    source = EXTENSION_MIGRATION.read_text(encoding="utf-8").lower()
    tree = ast.parse(EXTENSION_MIGRATION.read_text(encoding="utf-8"))
    expected_tables = {
        "stock_count_order",
        "stock_count_item",
        "transfer_order",
        "transfer_item",
        "approval_task",
    }
    expected_indexes = {
        "ix_stock_count_order_status_created_at",
        "ix_transfer_order_status_created_at",
        "ix_transfer_order_scope_status",
        "ix_approval_task_status_created_at",
        "ix_approval_task_requested_status",
    }
    expected_constraints = {
        "uq_stock_count_order_order_no",
        "uq_stock_count_item_line",
        "ck_stock_count_item_counted_nonnegative",
        "uq_transfer_order_order_no",
        "uq_transfer_item_line",
        "ck_transfer_item_quantity_positive",
        "ck_transfer_item_locations_different",
        "uq_approval_business",
    }

    assert _first_argument_strings(tree, "_create_table_if_missing") == expected_tables
    assert _first_argument_strings(tree, "_create_index_if_missing") == expected_indexes
    for constraint_name in expected_constraints:
        assert f'name="{constraint_name}"' in source


def test_extension_migration_uses_mysql_unsigned_integers_and_safe_downgrade():
    assert EXTENSION_MIGRATION.exists()
    source = EXTENSION_MIGRATION.read_text(encoding="utf-8").lower()

    assert "integer(unsigned=true)" in source
    assert "raise notimplementederror" in source
