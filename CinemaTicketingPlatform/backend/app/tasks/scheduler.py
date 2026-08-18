import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.core.runtime import load_runtime
from app.db.session import SessionLocal
from app.services.maintenance import run_maintenance

logger = logging.getLogger("uvicorn.error")


def _maintenance_job() -> None:
    db = SessionLocal()
    try:
        result = run_maintenance(db)
        if any(result.values()):
            logger.info("维护任务完成: %s", result)
    except Exception:
        logger.exception("维护任务执行失败")
        db.rollback()
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler | None:
    if not settings.SCHEDULER_ENABLED:
        return None
    # 桌面端首次运行（尚无数据库配置）时跳过维护任务
    rt = load_runtime()
    if rt.get("db_host") is None:
        from app.core.runtime import config_path

        if config_path() is not None:
            return None
    scheduler = BackgroundScheduler(timezone=settings.TZ)
    scheduler.add_job(
        _maintenance_job,
        "interval",
        seconds=30,
        id="maintenance",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info("后台维护任务已启动（每 30 秒）")
    return scheduler
