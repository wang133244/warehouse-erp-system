"""Create or update the standard roles using an explicitly supplied database URL."""
from __future__ import annotations  # 允许前置注解

import argparse  # 解析 --database-url
from sqlalchemy import create_engine, select  # 独立引擎，不走应用默认库
from sqlalchemy.orm import Session  # 会话

from backend.app.models import Role  # 角色表

STANDARD_ROLES = {  # 系统内置角色：编码 -> 中文名
    "admin": "系统管理员",  # 不限制仓库
    "warehouse_manager": "仓库管理员",  # 仓管
    "warehouse_operator": "仓库操作员",  # 操作员（长名）
    "operator": "仓库操作员",  # 操作员（短名，兼容旧数据）
    "viewer": "只读查看者",  # 只读
}  # 标准角色结束


def main(argv: list[str] | None = None) -> int:  # 入口，返回进程退出码
    parser = argparse.ArgumentParser(description="初始化标准 RBAC 角色")  # 命令说明
    parser.add_argument("--database-url", required=True)  # 必须显式给 URL，避免误连默认库
    args = parser.parse_args(argv)  # 解析参数
    engine = create_engine(args.database_url, pool_pre_ping=True)  # 一次性引擎
    try:  # 确保 finally 释放连接
        with Session(engine) as db:  # 短会话
            for role_code, role_name in STANDARD_ROLES.items():  # 逐个幂等写入
                if db.scalar(select(Role).where(Role.role_code == role_code)) is None:  # 尚不存在
                    db.add(Role(role_code=role_code, role_name=role_name))  # 插入标准角色
            db.commit()  # 一次性提交
    finally:  # 无论成败
        engine.dispose()  # 关掉连接池
    print("标准角色已初始化")  # 给运维看的成功提示
    return 0  # 成功


if __name__ == "__main__":  # 直接 python 运行时
    raise SystemExit(main())  # 把返回码交给 shell
