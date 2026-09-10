from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.db.session import get_db
from backend.app.dependencies import get_current_user, get_user_roles
from backend.app.schemas.auth import CurrentUserResponse, LoginRequest, TokenResponse
from backend.app.services.auth_service import authenticate

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    result = authenticate(db, payload.username, payload.password)
    if result is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    _, token = result
    return TokenResponse(access_token=token, expires_in=get_settings().access_token_expire_minutes * 60)


@router.get("/me", response_model=CurrentUserResponse)
def me(
    current_user: Annotated[object, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CurrentUserResponse:
    # get_current_user returns UserAccount; object avoids an ORM/pydantic coupling in route metadata.
    user = current_user
    return CurrentUserResponse(
        user_id=user.user_id,
        username=user.username,
        display_name=user.display_name,
        roles=get_user_roles(db, user.user_id),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(_: Annotated[object, Depends(get_current_user)]) -> None:
    """JWT is stateless; clients must discard the access token. Token revocation is an optional extension."""
    return None
