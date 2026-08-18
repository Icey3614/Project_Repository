import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import BizError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise BizError("未认证", code=401, status_code=401)
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise BizError("登录已过期", code=401, status_code=401)
    except jwt.InvalidTokenError:
        raise BizError("无效的登录凭证", code=401, status_code=401)
    user = db.get(User, int(payload.get("sub", 0)))
    if user is None:
        raise BizError("用户不存在", code=401, status_code=401)
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "ADMIN":
        raise BizError("需要管理员权限", code=403, status_code=403)
    return user
