from fastapi import APIRouter

from app.api import (
    admin,
    auth,
    movies,
    orders,
    payments,
    refunds,
    setup,
    sessions,
    tickets,
    transfers,
    venues,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(movies.router, prefix="/movies", tags=["电影"])
api_router.include_router(venues.router, prefix="/venues", tags=["场馆"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["场次"])
api_router.include_router(orders.router, prefix="/orders", tags=["订单"])
api_router.include_router(tickets.router, prefix="/tickets", tags=["票"])
api_router.include_router(payments.router, prefix="/payments", tags=["支付"])
api_router.include_router(refunds.router, prefix="/refund-requests", tags=["退款"])
api_router.include_router(transfers.router, prefix="/transfers", tags=["转赠"])
api_router.include_router(admin.router, prefix="/admin", tags=["管理"])
api_router.include_router(setup.router, prefix="/setup", tags=["首次运行配置"])
