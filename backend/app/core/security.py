"""密码 PBKDF2-SHA256（盐写在哈希串里）与 JWT 签发/校验。"""
from __future__ import annotations  # 允许前置注解

from datetime import UTC, datetime, timedelta  # JWT 的签发与过期时间
import hashlib  # PBKDF2 摘要
import hmac  # 恒定时间比较，防止时序攻击
import os  # 生成随机盐
import uuid  # 生成令牌 jti
from typing import Any  # JWT payload 的宽松类型

import jwt  # PyJWT 编解码

from backend.app.core.config import get_settings  # 读取密钥与过期分钟数

_HASH_NAME = "sha256"  # 口令哈希算法名
_ITERATIONS = 310_000  # PBKDF2 迭代次数，提高暴力破解成本


def hash_password(password: str) -> str:  # 把明文口令编成可存储的哈希串
    if not password:  # 拒绝空口令
        raise ValueError("密码不能为空")  # 调用方应先做长度校验
    salt = os.urandom(16)  # 16 字节随机盐，每个口令独立
    digest = hashlib.pbkdf2_hmac(_HASH_NAME, password.encode("utf-8"), salt, _ITERATIONS)  # 派生密钥
    return f"pbkdf2_{_HASH_NAME}${_ITERATIONS}${salt.hex()}${digest.hex()}"  # 方案、迭代、盐、摘要拼成一串


def verify_password(password: str, encoded: str) -> bool:  # 校验明文是否匹配存储哈希
    try:  # 格式不对或解码失败都视为不匹配
        scheme, iterations, salt_hex, expected_hex = encoded.split("$", 3)  # 拆出四段
        if scheme != f"pbkdf2_{_HASH_NAME}":  # 只接受本模块写出的方案
            return False  # 未知方案一律失败
        actual = hashlib.pbkdf2_hmac(  # 用同一参数重算摘要
            _HASH_NAME, password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)  # 盐从十六进制还原
        )  # pbkdf2 调用结束
        return hmac.compare_digest(actual.hex(), expected_hex)  # 恒定时间比较十六进制
    except (AttributeError, ValueError, TypeError):  # 非字符串、段数不对、hex 非法等
        return False  # 不抛给调用方，当作口令错误


def create_access_token(*, user_id: int, username: str, roles: list[str]) -> str:  # 签发 HS256 访问令牌
    settings = get_settings()  # 取密钥与过期配置
    now = datetime.now(UTC)  # 用 UTC 避免时区歧义
    payload: dict[str, Any] = {  # JWT 声明
        "sub": str(user_id),  # 主题：用户主键
        "username": username,  # 便于日志与前端展示
        "roles": roles,  # 签发时的角色快照
        "jti": uuid.uuid4().hex,  # 唯一 ID，登出时拉黑
        "iat": now,  # 签发时间
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),  # 过期时间
    }  # payload 结束
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")  # 用配置密钥签名


def decode_access_token(token: str) -> dict[str, Any]:  # 校验签名与 exp 后返回 payload
    settings = get_settings()  # 与签发使用同一密钥
    return jwt.decode(token, settings.secret_key, algorithms=["HS256"])  # 只允许 HS256，拒绝算法混淆
