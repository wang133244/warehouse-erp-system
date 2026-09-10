"""JWT and password helpers. Password hashes use PBKDF2-SHA256 and include their salt."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import os
from typing import Any

import jwt

from backend.app.core.config import get_settings

_HASH_NAME = "sha256"
_ITERATIONS = 310_000


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("密码不能为空")
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(_HASH_NAME, password.encode("utf-8"), salt, _ITERATIONS)
    return f"pbkdf2_{_HASH_NAME}${_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, iterations, salt_hex, expected_hex = encoded.split("$", 3)
        if scheme != f"pbkdf2_{_HASH_NAME}":
            return False
        actual = hashlib.pbkdf2_hmac(
            _HASH_NAME, password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(actual.hex(), expected_hex)
    except (AttributeError, ValueError, TypeError):
        return False


def create_access_token(*, user_id: int, username: str, roles: list[str]) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "username": username,
        "roles": roles,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
