"""Explicitly run Alembic migrations against a chosen non-default database."""

from __future__ import annotations  # 允许前置注解

import argparse  # 解析 URL、版本、sql 开关
import sys  # 错误打到 stderr
from pathlib import Path  # 定位 alembic.ini

from alembic import command  # 调用 upgrade 执行版本升级
from alembic.config import Config  # 运行时配置
from sqlalchemy.engine import make_url  # 解析库名做保护

BACKEND_DIR = Path(__file__).resolve().parents[1]  # scripts 的上一级即 backend


def _build_parser() -> argparse.ArgumentParser:  # 构造参数
    parser = argparse.ArgumentParser(description="运行增量数据库迁移")  # 说明
    parser.add_argument(  # 目标库
        "--database-url",  # 必须显式
        required=True,  # 不读默认业务 URL
        help="显式提供目标数据库 URL；不会使用默认业务数据库 URL",  # 帮助
    )  # database-url 结束
    parser.add_argument("--revision", default="head", help="迁移目标版本，默认 head")  # 可停在某 revision
    parser.add_argument("--sql", action="store_true", help="仅生成 SQL，不连接数据库")  # 离线打印
    parser.add_argument(  # 保护生产库名
        "--allow-erp-wms",  # 必须显式确认
        action="store_true",  # 开关
        help="明确确认允许将迁移执行到数据库名为 erp_wms 的目标",  # 帮助
    )  # allow-erp-wms 结束
    return parser  # 返回解析器


def _database_name(database_url: str) -> str | None:  # 从 URL 取出库名
    return make_url(database_url).database  # 可能为 None（SQLite 等）


def _build_alembic_config(database_url: str) -> Config:  # 指向本仓库 alembic
    config = Config(str(BACKEND_DIR / "alembic.ini"))  # 读 ini
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))  # 版本目录
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))  # ConfigParser 要转义百分号
    return config  # 交给 command.upgrade


def main(argv: list[str] | None = None) -> int:  # 入口
    args = _build_parser().parse_args(argv)  # 解析
    database_name = _database_name(args.database_url)  # 目标库名
    if database_name and database_name.lower() == "erp_wms" and not args.allow_erp_wms:  # 未确认就拒绝默认业务库
        print(  # 提示如何继续
            "为避免误操作，目标数据库为 erp_wms；如已完成备份并确认目标，请追加 --allow-erp-wms。",  # 中文说明
            file=sys.stderr,  # 错误流
        )  # print 结束
        return 2  # 约定：需要确认

    config = _build_alembic_config(args.database_url)  # 注入 URL
    try:  # Alembic/数据库运行时错误
        if args.sql:  # 只出 SQL
            command.upgrade(config, args.revision, sql=True)  # 不连库
        else:  # 真正执行
            command.upgrade(config, args.revision)  # 升到指定版本
    except Exception as exc:  # pragma: no cover - 依赖 Alembic 与数据库运行时
        print(f"数据库迁移失败: {exc}", file=sys.stderr)  # 失败原因
        return 1  # 失败

    print(f"数据库迁移完成: {args.revision}")  # 成功
    return 0  # 成功


if __name__ == "__main__":  # 直接运行
    raise SystemExit(main())  # 退出码
