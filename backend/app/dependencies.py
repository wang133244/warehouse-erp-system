from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.security import decode_access_token
from backend.app.db.models import Role, UserAccount, UserRole
from backend.app.db.session import get_db

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> UserAccount:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供访问令牌")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="访问令牌无效") from None
    user = db.get(UserAccount, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号不可用")
    return user


def get_user_roles(db: Session, user_id: int) -> list[str]:
    statement = (
        select(Role.role_code)
        .join(UserRole, UserRole.role_id == Role.role_id)
        .where(UserRole.user_id == user_id)
        .order_by(Role.role_code)
    )
    return list(db.scalars(statement))


def require_roles(*allowed_roles: str):
    def checker(
        current_user: Annotated[UserAccount, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_db)],
    ) -> UserAccount:
        roles = set(get_user_roles(db, current_user.user_id))
        if allowed_roles and not roles.intersection(allowed_roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="没有执行此操作的权限")
        return current_user

    return checker
