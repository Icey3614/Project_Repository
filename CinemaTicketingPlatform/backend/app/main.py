import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import BizError
from app.core.runtime import apply_runtime_to_settings
from app.tasks.scheduler import start_scheduler

logger = logging.getLogger("uvicorn.error")

apply_runtime_to_settings(settings)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = start_scheduler()
    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, version="0.6.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(BizError)
    async def biz_error_handler(request: Request, exc: BizError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message, "data": None},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"code": 422, "message": "参数校验失败", "data": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        logger.exception("未处理异常: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": "系统内部错误", "data": None},
        )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    app.include_router(api_router, prefix=settings.API_PREFIX)

    # 桌面端：托管前端构建产物并支持 SPA 路由回退
    dist = settings.frontend_dist_path
    if dist:
        assets = Path(dist) / "assets"
        if assets.exists():
            app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_fallback(full_path: str):
            if full_path.startswith("api/") or full_path in (
                "docs",
                "redoc",
                "openapi.json",
            ):
                return JSONResponse(
                    status_code=404,
                    content={"code": 404, "message": "Not Found", "data": None},
                )
            index = Path(dist) / "index.html"
            if index.exists():
                return FileResponse(str(index))
            return JSONResponse(
                status_code=404,
                content={"code": 404, "message": "前端资源缺失", "data": None},
            )
    return app


app = create_app()
