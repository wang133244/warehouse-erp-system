"""Explicitly run Alembic migrations against a chosen non-default database."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="运行增量数据库迁移")
    parser.add_argument(
        "--database-url",
        required=True,
        help="显式提供目标数据库 URL；不会使用默认业务数据库 URL",
    )
    parser.add_argument("--revision", default="head", help="迁移目标版本，默认 head")
    parser.add_argument("--sql", action="store_true", help="仅生成 SQL，不连接数据库")
    parser.add_argument(
        "--allow-erp-wms",
        action="store_true",
        help="明确确认允许将迁移执行到数据库名为 erp_wms 的目标",
    )
    return parser


def _database_name(database_url: str) -> str | None:
    return make_url(database_url).database


def _build_alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    database_name = _database_name(args.database_url)
    if database_name and database_name.lower() == "erp_wms" and not args.allow_erp_wms:
        print(
            "为避免误操作，目标数据库为 erp_wms；如已完成备份并确认目标，请追加 --allow-erp-wms。",
            file=sys.stderr,
        )
        return 2

    config = _build_alembic_config(args.database_url)
    try:
        if args.sql:
            command.upgrade(config, args.revision, sql=True)
        else:
            command.upgrade(config, args.revision)
    except Exception as exc:  # pragma: no cover - depends on Alembic/database runtime
        print(f"数据库迁移失败: {exc}", file=sys.stderr)
        return 1

    print(f"数据库迁移完成: {args.revision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

