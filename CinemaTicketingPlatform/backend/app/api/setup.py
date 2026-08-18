import re
import socket

import pymysql
from fastapi import APIRouter

from app.core.config import settings
from app.core.exceptions import BizError
from app.core.runtime import apply_runtime_to_settings, load_runtime, save_runtime
from app.db import session as db_session
from app.db.base import Base
from app.schemas.common import Envelope
from app.schemas.setup import SetupAlipay, SetupDatabase

router = APIRouter()

_DB_NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")


def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


def _db_reachable() -> bool:
    """实际尝试连接当前配置的数据库。"""
    try:
        from sqlalchemy import text

        engine = db_session.get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@router.get("/status", response_model=Envelope[dict])
def setup_status():
    rt = load_runtime()
    host = rt.get("db_host") or settings.DB_HOST
    port = int(rt.get("db_port") or settings.DB_PORT)
    db_configured = _db_reachable()
    return Envelope(
        data={
            "db_configured": db_configured,
            "alipay_configured": bool(rt.get("alipay_app_id") or settings.ALIPAY_APP_ID),
            "pay_provider": rt.get("pay_provider") or settings.PAYMENT_PROVIDER,
            "mysql_running": _port_open(host, port),
        }
    )


@router.post("/database", response_model=Envelope[dict])
def setup_database(payload: SetupDatabase):
    if not _port_open(payload.host, payload.port):
        raise BizError("无法连接 MySQL 服务器，请确认本机 MySQL 已启动", code=4000)
    if not _DB_NAME_RE.match(payload.db_name):
        raise BizError("数据库名仅支持字母、数字、下划线", code=4000)
    conn = None
    try:
        conn = pymysql.connect(
            host=payload.host,
            port=payload.port,
            user=payload.username,
            password=payload.password,
            connect_timeout=5,
        )
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{payload.db_name}` "
                "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
    except pymysql.err.OperationalError as exc:
        raise BizError(f"数据库连接失败：{exc}", code=4000)
    finally:
        if conn is not None:
            conn.close()

    rt = load_runtime()
    rt.update(
        db_host=payload.host,
        db_port=payload.port,
        db_user=payload.username,
        db_password=payload.password,
        db_name=payload.db_name,
    )
    save_runtime(rt)
    apply_runtime_to_settings(settings)
    db_session.reconfigure()

    import app.models  # noqa: F401  注册全部模型

    Base.metadata.create_all(bind=db_session.get_engine())
    from app.seed import seed

    seed()
    return Envelope(data={"created": True, "db_name": payload.db_name})


@router.post("/alipay", response_model=Envelope[dict])
def setup_alipay(payload: SetupAlipay):
    rt = load_runtime()
    use_mock = not payload.app_id
    rt.update(
        alipay_app_id=payload.app_id,
        alipay_private_key=payload.private_key,
        alipay_public_key=payload.public_key,
        alipay_notify_url=payload.notify_url,
        pay_provider="mock" if use_mock else "alipay",
    )
    save_runtime(rt)
    apply_runtime_to_settings(settings)
    return Envelope(
        data={
            "alipay_configured": not use_mock,
            "pay_provider": "mock" if use_mock else "alipay",
        }
    )
