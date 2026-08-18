from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.runtime import load_runtime

_engine = None
_factory = None


def _build() -> None:
    """根据运行时配置（优先）或 .env 配置构建数据库连接。"""
    global _engine, _factory
    rt = load_runtime()
    host = rt.get("db_host") or settings.DB_HOST
    port = rt.get("db_port") or settings.DB_PORT
    user = rt.get("db_user") or settings.DB_USER
    password = rt.get("db_password") or settings.DB_PASSWORD
    name = rt.get("db_name") or settings.DB_NAME
    url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4"
    _engine = create_engine(
        url,
        pool_pre_ping=True,
        pool_size=5,
        pool_recycle=3600,
        echo=False,
    )
    _factory = sessionmaker(
        bind=_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


def SessionLocal():
    """惰性会话工厂：首次调用或 reconfigure 后按最新配置构建。"""
    if _factory is None:
        _build()
    return _factory()


def get_engine():
    if _engine is None:
        _build()
    return _engine


def reconfigure() -> None:
    global _engine, _factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _factory = None
    _build()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
