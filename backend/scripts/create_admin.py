"""Create a local administrator without storing a password in source code."""
from __future__ import annotations

import argparse
import getpass
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.app.core.security import hash_password
from backend.app.db.models import Role, UserAccount, UserRole


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="创建或更新管理员账号")
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--display-name", default="系统管理员")
    parser.add_argument("--password", help="不建议使用；省略后从安全终端输入")
    args = parser.parse_args(argv)
    password = args.password or getpass.getpass("管理员密码: ")
    if len(password) < 8:
        parser.error("密码至少为 8 位")
    engine = create_engine(args.database_url, pool_pre_ping=True)
    try:
        with Session(engine) as db:
            admin = db.scalar(select(Role).where(Role.role_code == "admin"))
            if admin is None:
                parser.error("缺少 admin 角色，请先运行 seed_roles")
            user = db.scalar(select(UserAccount).where(UserAccount.username == args.username))
            if user is None:
                user = UserAccount(username=args.username, display_name=args.display_name, password_hash=hash_password(password), is_active=True)
                db.add(user); db.flush()
            else:
                user.display_name = args.display_name
                user.password_hash = hash_password(password)
                user.is_active = True
            if db.get(UserRole, {"user_id": user.user_id, "role_id": admin.role_id}) is None:
                db.add(UserRole(user_id=user.user_id, role_id=admin.role_id))
            db.commit()
    finally:
        engine.dispose()
    print(f"管理员账号已就绪: {args.username}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
