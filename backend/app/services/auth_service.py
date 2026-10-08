"""校验密码并签发 JWT。"""

from sqlalchemy import select  # 按用户名查找账号
from sqlalchemy.orm import Session  # 只读查用户，登录不改库存

from backend.app.core.security import create_access_token, verify_password  # 验密与签发访问令牌
from backend.app.models import UserAccount  # 用户账号表
from backend.app.dependencies import get_user_roles  # 读取角色写入 JWT


def authenticate(db: Session, username: str, password: str) -> tuple[UserAccount, str] | None:  # 校验凭据成功则返回用户与 JWT
    user = db.scalar(select(UserAccount).where(UserAccount.username == username))  # 按登录名取账号
    if user is None or not user.is_active or not verify_password(password, user.password_hash):  # 不存在、停用或密码错误一律失败
        return None  # 不泄露具体失败原因
    roles = get_user_roles(db, user.user_id)  # 读取角色列表，供仓管权限判断
    return user, create_access_token(user_id=user.user_id, username=user.username, roles=roles)  # 签发带用户与角色的访问令牌
