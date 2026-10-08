"""登录、登出、当前用户。登出把 JWT jti 写入黑名单。"""

from typing import Annotated  # 用于标注 FastAPI 依赖注入类型
import time  # 计算令牌剩余 TTL 时读取当前时间

from fastapi import APIRouter, Depends, HTTPException, status  # 路由、依赖、HTTP 异常与状态码
from fastapi.security import HTTPAuthorizationCredentials  # Bearer 凭证类型
from sqlalchemy.orm import Session  # ORM 会话类型

from backend.app.core.cache import get_cache  # 获取缓存客户端，用于 JWT 黑名单
from backend.app.core.config import get_settings  # 读取访问令牌过期配置
from backend.app.core.logging import get_logger  # 获取认证模块日志器
from backend.app.core.security import decode_access_token  # 解码 JWT 以取出 jti/exp
from backend.app.db.session import get_db  # 数据库会话依赖
from backend.app.dependencies import JWT_DENY_PREFIX, bearer_scheme, get_current_user, get_user_roles  # 黑名单前缀、Bearer 方案、当前用户与角色查询
from backend.app.schemas.auth import CurrentUserResponse, LoginRequest, TokenResponse  # 认证相关 DTO
from backend.app.services.auth_service import authenticate  # 校验账号密码并签发令牌

router = APIRouter(prefix="/auth", tags=["认证"])  # 认证路由，前缀 /auth
auth_logger = get_logger("auth")  # 认证操作日志器


@router.post("/login", response_model=TokenResponse)  # POST /auth/login，返回令牌
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:  # 登录：校验凭据并签发 JWT
    result = authenticate(db, payload.username, payload.password)  # 调用认证服务
    if result is None:  # 用户不存在、停用或密码错误
        auth_logger.warning("login failed username=%s", payload.username)  # 记录失败日志，不写密码
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")  # 返回 401
    user, token = result  # 解包用户实体与访问令牌
    auth_logger.info("login success username=%s user_id=%s", user.username, user.user_id)  # 记录登录成功
    return TokenResponse(access_token=token, expires_in=get_settings().access_token_expire_minutes * 60)  # 过期分钟换算为秒


@router.get("/me", response_model=CurrentUserResponse)  # GET /auth/me，查询当前用户
def me(  # 返回当前登录用户资料与角色
    current_user: Annotated[object, Depends(get_current_user)],  # 依赖注入当前用户
    db: Annotated[Session, Depends(get_db)],  # 数据库会话，用于查角色
) -> CurrentUserResponse:  # 响应模型为 CurrentUserResponse
    # get_current_user returns UserAccount; object avoids an ORM/pydantic coupling in route metadata.
    user = current_user  # 将依赖结果视为用户实体
    return CurrentUserResponse(  # 组装当前用户响应
        user_id=user.user_id,  # 用户主键
        username=user.username,  # 登录名
        display_name=user.display_name,  # 显示名
        roles=get_user_roles(db, user.user_id),  # 查询该用户角色编码
    )  # 返回当前用户 DTO


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)  # POST /auth/logout，成功无内容
def logout(  # 登出：把当前 JWT 的 jti 写入黑名单
    _: Annotated[object, Depends(get_current_user)],  # 要求已登录，占位不使用用户对象
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],  # 从 Authorization 取 Bearer
) -> None:  # 无响应体
    if credentials is None:  # 没有携带令牌则直接结束
        return None  # 幂等返回
    try:  # 解码失败时视为已失效，静默成功
        payload = decode_access_token(credentials.credentials)  # 解析 JWT 载荷
    except Exception:  # 任意解码异常
        return None  # 不抛错，避免登出接口失败
    jti = payload.get("jti")  # 取出令牌唯一标识
    if not jti:  # 无 jti 则无法拉黑
        return None  # 直接返回
    exp = payload.get("exp")  # UNIX 过期时间
    ttl = get_settings().access_token_expire_minutes * 60  # 默认 TTL 为配置的过期秒数
    if isinstance(exp, (int, float)):  # 载荷带有 exp 时按剩余寿命拉黑
        ttl = max(1, int(exp - time.time()))  # 至少保留 1 秒，避免立即过期键
    get_cache().set(f"{JWT_DENY_PREFIX}{jti}", "1", ttl)  # 写入黑名单，值为占位 "1"
    auth_logger.info("logout user_id=%s", payload.get("sub"))  # 记录登出用户
    return None  # 返回无内容的成功响应
