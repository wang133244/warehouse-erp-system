"""迁移脚本不含 DROP、不毁现网数据。"""

import ast  # import ast
from pathlib import Path  # from pathlib import Path
from importlib.util import module_from_spec, spec_from_file_location  # from importlib.util impo

import sqlalchemy as sa  # import sqlalchemy as sa


EXTENSION_MIGRATION = (  # EXTENSION_MIGRATION = (
    Path(__file__).parents[1] / "alembic" / "versions" / "0002_stock_count_transfer_approval.py"  # Path(__file__).parents[1
)  # )


def _first_argument_strings(tree: ast.Module, function_name: str) -> set[str]:  # def _first_argument_stri
    arguments = set()  # arguments = set()
    for node in ast.walk(tree):  # for node in ast.walk(tre
        if (  # if (
            isinstance(node, ast.Call)  # isinstance(node, ast.Cal
            and isinstance(node.func, ast.Name)  # and isinstance(node.func
            and node.func.id == function_name  # and node.func.id == func
            and node.args  # and node.args
        ):  # ):
            argument = node.args[0]  # argument = node.args[0]
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str):  # if isinstance(argument, 
                arguments.add(argument.value)  # arguments.add(argument.v
    return arguments  # return arguments


def test_initial_backend_migration_is_additive_only():  # def test_initial_backend
    migration = Path(__file__).parents[1] / "alembic" / "versions" / "0001_add_backend_core.py"  # migration = Path(__file_

    assert migration.exists()  # assert migration.exists(
    source = migration.read_text(encoding="utf-8").lower()  # source = migration.read_
    assert "add_column(\"stock_balance\"" in source  # assert 'add_column(\'sto
    assert "create_table(\"user_account\"" in source  # assert 'create_table(\'u
    assert "drop_table" not in source  # assert 'drop_table' not 
    assert "drop_column" not in source  # assert 'drop_column' not


def test_initial_backend_migration_uses_mysql_unsigned_integers():  # def test_initial_backend
    migration = Path(__file__).parents[1] / "alembic" / "versions" / "0001_add_backend_core.py"  # migration = Path(__file_

    source = migration.read_text(encoding="utf-8").lower()  # source = migration.read_
    assert "integer(unsigned=true)" in source  # assert 'integer(unsigned


def test_mysql_unsigned_integer_helper_is_not_recursive():  # def test_mysql_unsigned_
    from importlib.util import module_from_spec, spec_from_file_location  # from importlib.util impo

    migration = Path(__file__).parents[1] / "alembic" / "versions" / "0001_add_backend_core.py"  # migration = Path(__file_
    spec = spec_from_file_location("add_backend_core_migration", migration)  # spec = spec_from_file_lo
    module = module_from_spec(spec)  # module = module_from_spe
    assert spec is not None and spec.loader is not None  # assert spec is not None 
    spec.loader.exec_module(module)  # spec.loader.exec_module(

    column_type = module.mysql_unsigned_integer()  # column_type = module.mys

    assert column_type is not None  # assert column_type is no


def test_create_table_if_missing_passes_all_arguments(monkeypatch):  # def test_create_table_if
    migration = Path(__file__).parents[1] / "alembic" / "versions" / "0001_add_backend_core.py"  # migration = Path(__file_
    spec = spec_from_file_location("add_backend_core_migration", migration)  # spec = spec_from_file_lo
    module = module_from_spec(spec)  # module = module_from_spe
    assert spec is not None and spec.loader is not None  # assert spec is not None 
    spec.loader.exec_module(module)  # spec.loader.exec_module(

    calls = []  # calls = []
    monkeypatch.setattr(module.op, "create_table", lambda *args, **kwargs: calls.append(args))  # monkeypatch.setattr(modu
    monkeypatch.setattr(module, "_has_table", lambda table_name: False)  # monkeypatch.setattr(modu
    first = sa.Column("id", module.mysql_unsigned_integer(), primary_key=True)  # first = sa.Column('id', 
    second = sa.Column("name", sa.String(length=32), nullable=False)  # second = sa.Column('name
    constraint = sa.UniqueConstraint("name", name="uq_probe_name")  # constraint = sa.UniqueCo

    module._create_table_if_missing("probe", first, second, constraint)  # module._create_table_if_

    assert calls == [("probe", first, second, constraint)]  # assert calls == [('probe


def test_extension_migration_is_additive_and_depends_on_core():  # def test_extension_migra
    assert EXTENSION_MIGRATION.exists()  # assert EXTENSION_MIGRATI
    source = EXTENSION_MIGRATION.read_text(encoding="utf-8").lower()  # source = EXTENSION_MIGRA

    assert 'revision = "0002_stock_count_transfer_approval"' in source  # assert 'revision = '0002
    assert 'down_revision = "0001_add_backend_core"' in source  # assert 'down_revision = 
    assert "create_table" in source  # assert 'create_table' in
    assert "drop_table" not in source  # assert 'drop_table' not 
    assert "drop_column" not in source  # assert 'drop_column' not
    assert "drop_index" not in source  # assert 'drop_index' not 


def test_extension_migration_creates_guarded_tables_and_named_indexes():  # def test_extension_migra
    assert EXTENSION_MIGRATION.exists()  # assert EXTENSION_MIGRATI
    source = EXTENSION_MIGRATION.read_text(encoding="utf-8").lower()  # source = EXTENSION_MIGRA
    tree = ast.parse(EXTENSION_MIGRATION.read_text(encoding="utf-8"))  # tree = ast.parse(EXTENSI
    expected_tables = {  # expected_tables = {
        "stock_count_order",  # 'stock_count_order',
        "stock_count_item",  # 'stock_count_item',
        "transfer_order",  # 'transfer_order',
        "transfer_item",  # 'transfer_item',
        "approval_task",  # 'approval_task',
    }  # }
    expected_indexes = {  # expected_indexes = {
        "ix_stock_count_order_status_created_at",  # 'ix_stock_count_order_st
        "ix_transfer_order_status_created_at",  # 'ix_transfer_order_statu
        "ix_transfer_order_scope_status",  # 'ix_transfer_order_scope
        "ix_approval_task_status_created_at",  # 'ix_approval_task_status
        "ix_approval_task_requested_status",  # 'ix_approval_task_reques
    }  # }
    expected_constraints = {  # expected_constraints = {
        "uq_stock_count_order_order_no",  # 'uq_stock_count_order_or
        "uq_stock_count_item_line",  # 'uq_stock_count_item_lin
        "ck_stock_count_item_counted_nonnegative",  # 'ck_stock_count_item_cou
        "uq_transfer_order_order_no",  # 'uq_transfer_order_order
        "uq_transfer_item_line",  # 'uq_transfer_item_line',
        "ck_transfer_item_quantity_positive",  # 'ck_transfer_item_quanti
        "ck_transfer_item_locations_different",  # 'ck_transfer_item_locati
        "uq_approval_business",  # 'uq_approval_business',
    }  # }

    assert _first_argument_strings(tree, "_create_table_if_missing") == expected_tables  # assert _first_argument_s
    assert _first_argument_strings(tree, "_create_index_if_missing") == expected_indexes  # assert _first_argument_s
    for constraint_name in expected_constraints:  # for constraint_name in e
        assert f'name="{constraint_name}"' in source  # assert f'name='{constrai


def test_extension_migration_uses_mysql_unsigned_integers_and_safe_downgrade():  # def test_extension_migra
    assert EXTENSION_MIGRATION.exists()  # assert EXTENSION_MIGRATI
    source = EXTENSION_MIGRATION.read_text(encoding="utf-8").lower()  # source = EXTENSION_MIGRA

    assert "integer(unsigned=true)" in source  # assert 'integer(unsigned
    assert "raise notimplementederror" in source  # assert 'raise notimpleme


def test_alert_ack_updated_at_migration_is_additive():  # def test_alert_ack_updat
    migration = Path(__file__).parents[1] / "alembic" / "versions" / "0005_alert_ack_updated_at.py"  # migration = Path(__file_
    source = migration.read_text(encoding="utf-8").lower()  # source = migration.read_

    assert migration.exists()  # assert migration.exists(
    assert 'revision = "0005_alert_ack_updated_at"' in source  # assert 'revision = '0005
    assert 'down_revision = "0004_ops_hardening"' in source  # assert 'down_revision = 
    assert "alert_ack" in source  # assert 'alert_ack' in so
    assert "updated_at" in source  # assert 'updated_at' in s
    assert "add_column" in source  # assert 'add_column' in s
    assert "drop_table" not in source  # assert 'drop_table' not 
    assert "drop_column" not in source  # assert 'drop_column' not
    assert "raise notimplementederror" in source  # assert 'raise notimpleme
