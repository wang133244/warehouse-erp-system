from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.security import create_access_token, verify_password
from backend.app.db.models import UserAccount
from backend.app.dependencies import get_user_roles


def authenticate(db: Session, username: str, password: str) -> tuple[UserAccount, str] | None:
    user = db.scalar(select(UserAccount).where(UserAccount.username == username))
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        return None
    roles = get_user_roles(db, user.user_id)
    return user, create_access_token(user_id=user.user_id, username=user.username, roles=roles)
