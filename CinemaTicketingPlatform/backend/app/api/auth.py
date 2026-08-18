from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.exceptions import BizError
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Envelope
from app.schemas.user import LoginRequest, Token, UserCreate, UserOut

router = APIRouter()


@router.post("/register", response_model=Envelope[UserOut], status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    exists = db.scalar(select(User).where(User.username == payload.username))
    if exists is not None:
        raise BizError("用户名已存在", code=4001)
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        nickname=payload.nickname or payload.username,
        role="USER",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return Envelope(data=UserOut.model_validate(user))


@router.post("/login", response_model=Envelope[Token])
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise BizError("用户名或密码错误", code=4011, status_code=401)
    token = create_access_token(user.id, user.role)
    return Envelope(data=Token(access_token=token))


@router.get("/me", response_model=Envelope[UserOut])
def me(user: User = Depends(get_current_user)):
    return Envelope(data=UserOut.model_validate(user))
