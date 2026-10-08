"""Read-only database readiness check for the imported WMS database."""

from __future__ import annotations  # 允许前置注解

import argparse  # 解析 URL 与 --json
import json  # JSON 输出
import sys  # 改 sys.path、stderr
from pathlib import Path  # 定位仓库根
from typing import Any  # 报告字典

from sqlalchemy import create_engine, inspect  # 只读探活与结构检查
from sqlalchemy.engine import make_url  # 掩码密码

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # 仓库根，保证能 import backend
if str(PROJECT_ROOT) not in sys.path:  # 尚未加入
    sys.path.insert(0, str(PROJECT_ROOT))  # 以仓库根为 PYTHONPATH

BASELINE_TABLES = {  # 导入 WMS 必须存在的基础表
    "warehouse",  # 仓库
    "warehouse_location",  # 库位
    "product",  # 商品
    "staff",  # 员工
    "customer",  # 客户
    "stock_balance",  # 库存余额
    "inbound_record",  # 历史入库
    "outbound_record",  # 历史出库
    "data_import_batch",  # 导入批次
    "stock_ledger",  # 库存流水
}  # 基础表结束
BACKEND_TABLES = {  # 后端扩展表，缺了也能探活但功能不全
    "user_account",  # 账号
    "role",  # 角色
    "user_role",  # 用户角色
    "user_warehouse_scope",  # 仓库范围
    "inbound_order",  # 入库单
    "inbound_item",  # 入库明细
    "outbound_order",  # 出库单
    "outbound_item",  # 出库明细
    "picking_task",  # 拣货
    "audit_log",  # 审计
    "idempotency_record",  # 幂等
}  # 扩展表结束


def mask_database_url(database_url: str) -> str:  # 日志安全 URL
    """Return a log-safe URL with credentials hidden."""
    return make_url(database_url).render_as_string(hide_password=True)  # 隐藏密码


def inspect_database(database_url: str) -> dict[str, Any]:  # 连库只读检查表结构
    """Connect, inspect schema only, and return a JSON-serializable report."""
    engine = create_engine(database_url, pool_pre_ping=True)  # 一次性引擎
    try:  # 保证 dispose
        with engine.connect() as connection:  # 只开连接，不写
            database_inspector = inspect(connection)  # 结构检查器
            tables = set(database_inspector.get_table_names())  # 现有表名
            stock_columns = {  # stock_balance 列名，用于看 reserved_quantity
                column["name"] for column in database_inspector.get_columns("stock_balance")  # 列名集合
            } if "stock_balance" in tables else set()  # 表都不在则空集
            return {  # JSON 可序列化报告
                "database_url": mask_database_url(database_url),  # 已掩码
                "baseline_tables": sorted(BASELINE_TABLES & tables),  # 已有基础表
                "missing_baseline_tables": sorted(BASELINE_TABLES - tables),  # 缺的基础表
                "backend_tables": sorted(BACKEND_TABLES & tables),  # 已有扩展表
                "missing_backend_tables": sorted(BACKEND_TABLES - tables),  # 缺的扩展表
                "reserved_quantity_present": "reserved_quantity" in stock_columns,  # 预留字段是否已加
                "alembic_version_present": "alembic_version" in tables,  # 是否跑过迁移
            }  # 报告结束
    finally:  # 无论成败
        engine.dispose()  # 关池


def _build_parser() -> argparse.ArgumentParser:  # 构造参数
    parser = argparse.ArgumentParser(description="只读检查 WMS 数据库结构，不执行迁移")  # 说明
    parser.add_argument(  # 目标库
        "--database-url",  # 必须显式
        required=True,  # 不读带默认值的业务配置
        help="显式提供 SQLAlchemy 数据库 URL；不会读取带默认值的业务配置",  # 帮助
    )  # database-url 结束
    parser.add_argument("--json", action="store_true", help="以 JSON 输出检查结果")  # 机器可读
    return parser  # 解析器


def main(argv: list[str] | None = None) -> int:  # 入口
    args = _build_parser().parse_args(argv)  # 解析
    try:  # 连不上库等运行时错误
        report = inspect_database(args.database_url)  # 只读报告
    except Exception as exc:  # pragma: no cover - 依赖外部数据库是否可达
        print(f"数据库只读检查失败: {exc}", file=sys.stderr)  # 失败原因
        return 1  # 连接失败

    if args.json:  # JSON 模式
        print(json.dumps(report, ensure_ascii=False, indent=2))  # 保留中文
    else:  # 人类可读
        print(f"目标: {report['database_url']}")  # 掩码后的 URL
        print(f"基础导入表: {len(report['baseline_tables'])}/{len(BASELINE_TABLES)}")  # 基础表覆盖
        print(f"后端扩展表: {len(report['backend_tables'])}/{len(BACKEND_TABLES)}")  # 扩展表覆盖
        print(f"stock_balance.reserved_quantity: {'存在' if report['reserved_quantity_present'] else '不存在'}")  # 预留列
        if report["missing_baseline_tables"]:  # 缺基础表
            print("缺少基础表: " + ", ".join(report["missing_baseline_tables"]))  # 列出
        if report["missing_backend_tables"]:  # 缺扩展表
            print("缺少后端表: " + ", ".join(report["missing_backend_tables"]))  # 列出

    return 0 if not report["missing_baseline_tables"] else 2  # 缺基础表视为未就绪


if __name__ == "__main__":  # 直接运行
    raise SystemExit(main())  # 退出码
