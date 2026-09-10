"""Create or update the standard roles using an explicitly supplied database URL."""
from __future__ import annotations

import argparse
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.app.db.models import Role

STANDARD_ROLES = {
    "admin": "系统管理员",
    "warehouse_manager": "仓库管理员",
    "operator": "仓库操作员",
    "viewer": "只读查看者",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="初始化标准 RBAC 角色")
    parser.add_argument("--database-url", required=True)
    args = parser.parse_args(argv)
    engine = create_engine(args.database_url, pool_pre_ping=True)
    try:
        with Session(engine) as db:
            for role_code, role_name in STANDARD_ROLES.items():
                if db.scalar(select(Role).where(Role.role_code == role_code)) is None:
                    db.add(Role(role_code=role_code, role_name=role_name))
            db.commit()
    finally:
        engine.dispose()
    print("标准角色已初始化")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
