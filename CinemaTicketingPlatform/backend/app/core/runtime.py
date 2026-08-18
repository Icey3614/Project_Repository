"""首次运行配置管理：数据库与支付宝沙箱信息保存到本地 JSON 配置文件。"""

import json
import os
from pathlib import Path


def config_path() -> Path | None:
    raw = os.environ.get("CINEMA_CONFIG", "").strip()
    return Path(raw) if raw else None


def load_runtime() -> dict:
    path = config_path()
    if path is not None and path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_runtime(data: dict) -> None:
    path = config_path()
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def apply_runtime_to_settings(settings_obj) -> None:
    """将运行时配置（桌面端用户输入）合并到全局设置。"""
    rt = load_runtime()
    if rt.get("db_host"):
        settings_obj.DB_HOST = rt["db_host"]
        settings_obj.DB_PORT = int(rt.get("db_port") or settings_obj.DB_PORT)
        settings_obj.DB_USER = rt.get("db_user") or settings_obj.DB_USER
        settings_obj.DB_PASSWORD = rt.get("db_password") or ""
        settings_obj.DB_NAME = rt.get("db_name") or settings_obj.DB_NAME
    if rt.get("pay_provider") in ("alipay", "mock"):
        settings_obj.PAYMENT_PROVIDER = rt["pay_provider"]
    if rt.get("alipay_app_id"):
        settings_obj.ALIPAY_APP_ID = rt["alipay_app_id"]
        settings_obj.ALIPAY_PRIVATE_KEY = rt.get("alipay_private_key") or ""
        settings_obj.ALIPAY_PUBLIC_KEY = rt.get("alipay_public_key") or ""
        settings_obj.ALIPAY_NOTIFY_URL = rt.get("alipay_notify_url") or ""
