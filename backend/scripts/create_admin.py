"""Create a local administrator without storing a password in source code."""
from __future__ import annotations  # 允许前置注解

import argparse  # 解析命令行
import getpass  # 从终端隐式读密码
from sqlalchemy import create_engine, select  # 独立引擎
from sqlalchemy.orm import Session  # 会话

from backend.app.core.security import hash_password  # PBKDF2 哈希
from backend.app.models import Role, UserAccount, UserRole  # 账号与角色


def main(argv: list[str] | None = None) -> int:  # 入口
    parser = argparse.ArgumentParser(description="创建或更新管理员账号")  # 命令说明
    parser.add_argument("--database-url", required=True)  # 必须显式 URL
    parser.add_argument("--username", required=True)  # 登录名
    parser.add_argument("--display-name", default="系统管理员")  # 显示名
    parser.add_argument("--password", help="不建议使用；省略后从安全终端输入")  # 可选，避免进 shell 历史
    args = parser.parse_args(argv)  # 解析
    password = args.password or getpass.getpass("管理员密码: ")  # 优先参数，否则交互输入
    if len(password) < 8:  # 最短 8 位
        parser.error("密码至少为 8 位")  # argparse 错误并退出
    engine = create_engine(args.database_url, pool_pre_ping=True)  # 一次性引擎
    try:  # 释放连接
        with Session(engine) as db:  # 短会话
            admin = db.scalar(select(Role).where(Role.role_code == "admin"))  # 必须已有 admin 角色
            if admin is None:  # 没跑过 seed_roles
                parser.error("缺少 admin 角色，请先运行 seed_roles")  # 明确提示顺序
            user = db.scalar(select(UserAccount).where(UserAccount.username == args.username))  # 按登录名查找
            if user is None:  # 新建
                user = UserAccount(username=args.username, display_name=args.display_name, password_hash=hash_password(password), is_active=True)  # 启用状态
                db.add(user); db.flush()  # 先 flush 拿到 user_id
            else:  # 已存在则覆盖资料与口令
                user.display_name = args.display_name  # 更新显示名
                user.password_hash = hash_password(password)  # 重置哈希
                user.is_active = True  # 重新启用
            if db.get(UserRole, {"user_id": user.user_id, "role_id": admin.role_id}) is None:  # 尚未绑定 admin
                db.add(UserRole(user_id=user.user_id, role_id=admin.role_id))  # 补角色
            db.commit()  # 提交账号与角色
    finally:  # 无论成败
        engine.dispose()  # 关池
    print(f"管理员账号已就绪: {args.username}")  # 成功提示，不含密码
    return 0  # 成功


if __name__ == "__main__":  # 直接运行
    raise SystemExit(main())  # 退出码
