"""Read-only database readiness check for the imported WMS database."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BASELINE_TABLES = {
    "warehouse",
    "warehouse_location",
    "product",
    "staff",
    "customer",
    "stock_balance",
    "inbound_record",
    "outbound_record",
    "data_import_batch",
    "stock_ledger",
}
BACKEND_TABLES = {
    "user_account",
    "role",
    "user_role",
    "user_warehouse_scope",
    "inbound_order",
    "inbound_item",
    "outbound_order",
    "outbound_item",
    "picking_task",
    "audit_log",
    "idempotency_record",
}


def mask_database_url(database_url: str) -> str:
    """Return a log-safe URL with credentials hidden."""
    return make_url(database_url).render_as_string(hide_password=True)


def inspect_database(database_url: str) -> dict[str, Any]:
    """Connect, inspect schema only, and return a JSON-serializable report."""
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            database_inspector = inspect(connection)
            tables = set(database_inspector.get_table_names())
            stock_columns = {
                column["name"] for column in database_inspector.get_columns("stock_balance")
            } if "stock_balance" in tables else set()
            return {
                "database_url": mask_database_url(database_url),
                "baseline_tables": sorted(BASELINE_TABLES & tables),
                "missing_baseline_tables": sorted(BASELINE_TABLES - tables),
                "backend_tables": sorted(BACKEND_TABLES & tables),
                "missing_backend_tables": sorted(BACKEND_TABLES - tables),
                "reserved_quantity_present": "reserved_quantity" in stock_columns,
                "alembic_version_present": "alembic_version" in tables,
            }
    finally:
        engine.dispose()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="只读检查 WMS 数据库结构，不执行迁移")
    parser.add_argument(
        "--database-url",
        required=True,
        help="显式提供 SQLAlchemy 数据库 URL；不会读取带默认值的业务配置",
    )
    parser.add_argument("--json", action="store_true", help="以 JSON 输出检查结果")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        report = inspect_database(args.database_url)
    except Exception as exc:  # pragma: no cover - depends on external database
        print(f"数据库只读检查失败: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"目标: {report['database_url']}")
        print(f"基础导入表: {len(report['baseline_tables'])}/{len(BASELINE_TABLES)}")
        print(f"后端扩展表: {len(report['backend_tables'])}/{len(BACKEND_TABLES)}")
        print(f"stock_balance.reserved_quantity: {'存在' if report['reserved_quantity_present'] else '不存在'}")
        if report["missing_baseline_tables"]:
            print("缺少基础表: " + ", ".join(report["missing_baseline_tables"]))
        if report["missing_backend_tables"]:
            print("缺少后端表: " + ", ".join(report["missing_backend_tables"]))

    return 0 if not report["missing_baseline_tables"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
