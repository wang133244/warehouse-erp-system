"""请求依赖：解析 JWT、当前用户、RBAC、仓库数据范围。登出后的 jti 在缓存黑名单中拒绝。"""

from __future__ import annotations  # 允许类型注解引用尚未定义的符号

from typing import Annotated  # 用 Annotated 把依赖注入写进参数类型

import jwt  # 捕获 PyJWT 解码错误
from fastapi import Depends, HTTPException, status  # FastAPI 依赖与 HTTP 异常
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer  # Bearer 令牌解析
from sqlalchemy import select  # 构造查询语句
from sqlalchemy.orm import Session  # 数据库会话类型

from backend.app.core.cache import get_cache  # 读取 JWT 黑名单缓存
from backend.app.core.errors import AppError  # 业务权限错误
from backend.app.core.logging import get_logger  # 鉴权相关日志
from backend.app.core.security import decode_access_token  # 校验并解码 JWT
from backend.app.db.session import get_db  # 请求级数据库会话
from backend.app.models import Role, UserAccount, UserRole, UserWarehouseScope  # 账号、角色与仓库范围表

JWT_DENY_PREFIX = "erp:jwt:deny:"  # 登出作废令牌在缓存中的键前缀
auth_logger = get_logger("auth")  # 鉴权日志记录器

bearer_scheme = HTTPBearer(auto_error=False)  # 缺少 Authorization 时不自动 403，由本模块统一 401


def get_current_user(  # 从 Bearer JWT 解析当前登录用户
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],  # 可选的 Authorization 头
    db: Annotated[Session, Depends(get_db)],  # 当前请求的数据库会话
) -> UserAccount:  # 返回仍有效的用户账号
    if credentials is None:  # 请求未带令牌
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供访问令牌")  # 明确告知缺少令牌
    try:  # 解码 JWT 并检查黑名单
        payload = decode_access_token(credentials.credentials)  # 用密钥校验签名与过期时间
        user_id = int(payload["sub"])  # sub 存的是用户主键字符串
        jti = payload.get("jti")  # 令牌唯一 ID，登出时写入黑名单
        if jti and get_cache().get(f"{JWT_DENY_PREFIX}{jti}"):  # 该 jti 已被登出作废
            auth_logger.info("jwt denied user_id=%s", user_id)  # 记录被拒绝的用户，便于审计
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="访问令牌无效")  # 对外不区分作废原因
    except HTTPException:  # 上面主动抛出的 401 原样上抛
        raise  # 不包装、不改状态码
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):  # 签名错误、缺字段或类型不对
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="访问令牌无效") from None  # 隐藏底层异常链
    user = db.get(UserAccount, user_id)  # 按主键加载账号
    if user is None or not user.is_active:  # 账号不存在或已停用
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号不可用")  # 同样返回 401
    return user  # 通过校验的当前用户


def get_user_roles(db: Session, user_id: int) -> list[str]:  # 查询用户全部角色编码，保持稳定顺序
    statement = (  # 通过 user_role 关联 role 表
        select(Role.role_code)  # 只要角色编码
        .join(UserRole, UserRole.role_id == Role.role_id)  # 用户-角色多对多
        .where(UserRole.user_id == user_id)  # 限定当前用户
        .order_by(Role.role_code)  # 按编码排序，结果可复现
    )  # 查询语句结束
    return list(db.scalars(statement))  # 物化成字符串列表


def get_current_user_roles(db: Session, user_id: int) -> set[str]:  # 角色集合，便于做交集判断
    return set(get_user_roles(db, user_id))  # 转成集合去重


def granted_warehouse_ids(db: Session, user_id: int, roles: set[str]) -> set[int] | None:  # 计算用户可操作的仓库主键集合
    # None 表示管理员不限制仓库；空集合表示非管理员未绑定任何仓。
    if "admin" in roles:  # 管理员跨仓，不做范围裁剪
        return None  # None 表示不限制
    return set(  # 非管理员只看绑定过的仓库
        db.scalars(  # 取出仓库 ID 标量
            select(UserWarehouseScope.warehouse_id).where(  # 用户仓库范围表
                UserWarehouseScope.user_id == user_id  # 当前用户的绑定行
            )  # where 结束
        )  # scalars 结束
    )  # 转成 set


def require_granted_warehouses(db: Session, user_id: int, roles: set[str]) -> set[int] | None:  # 要求至少有一个可操作仓库
    granted = granted_warehouse_ids(db, user_id, roles)  # 先算出范围
    if granted is not None and not granted:  # 非管理员且未绑定任何仓
        raise AppError("WAREHOUSE_SCOPE_FORBIDDEN", "没有目标仓库的操作权限", 403)  # 禁止继续操作
    return granted  # 管理员为 None；其他人返回已绑定集合


def ensure_warehouse_scope(  # 校验请求涉及的仓库是否都在授权范围内
    db: Session,  # 数据库会话
    user_id: int,  # 当前用户
    roles: set[str],  # 已解析的角色
    warehouse_ids: set[int],  # 本次操作触及的仓库
) -> None:  # 无返回值，越权则抛错
    if "admin" in roles:  # 管理员跳过范围检查
        return  # 直接放行
    granted = set(  # 再查一遍绑定仓库，避免调用方传入过期集合
        db.scalars(  # 取出仓库 ID
            select(UserWarehouseScope.warehouse_id).where(  # 范围表
                UserWarehouseScope.user_id == user_id  # 当前用户
            )  # where 结束
        )  # scalars 结束
    )  # 授权仓库集合
    if not warehouse_ids.issubset(granted):  # 存在未授权仓库
        raise AppError("WAREHOUSE_SCOPE_FORBIDDEN", "没有目标仓库的操作权限", 403)  # 拒绝越权


def require_roles(*allowed_roles: str):  # 生成“必须具备所列角色之一”的依赖
    def checker(  # 实际注入到路由的检查函数
        current_user: Annotated[UserAccount, Depends(get_current_user)],  # 先解析当前用户
        db: Annotated[Session, Depends(get_db)],  # 再取会话查角色
    ) -> UserAccount:  # 通过后把用户交回路由
        roles = set(get_user_roles(db, current_user.user_id))  # 当前用户角色集合
        if allowed_roles and not roles.intersection(allowed_roles):  # 指定了角色但没有任何交集
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="没有执行此操作的权限")  # 禁止访问
        return current_user  # 角色匹配，放行

    return checker  # 把闭包交给 FastAPI Depends
