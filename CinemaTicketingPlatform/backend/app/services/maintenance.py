from sqlalchemy.orm import Session

from app.services.order_service import auto_checkin, release_at_cutoff, release_expired_locks


def run_maintenance(db: Session) -> dict:
    """定时维护：超时释放 + 停售/支付截止强制释放 + 开场自动核销。"""
    expired = release_expired_locks(db)
    cutoff = release_at_cutoff(db)
    checked = auto_checkin(db)
    db.commit()
    return {"expired": expired, "cutoff": cutoff, "checkin": checked}
