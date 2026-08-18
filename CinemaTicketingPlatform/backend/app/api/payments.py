from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BizError, NotFoundError
from app.db.session import get_db
from app.models.order import Order
from app.models.payment import Payment
from app.models.ticket import Ticket
from app.payments.factory import get_payment_provider
from app.services.payment_service import confirm_paid_order

router = APIRouter()


@router.post("/{trade_no}/callback")
async def payment_callback(
    trade_no: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """支付异步回调：验签 + 幂等处理（mock 场景下已即时成功，此接口兜底）。"""
    content_type = request.headers.get("content-type", "")
    if "json" in content_type:
        payload = await request.json()
    else:
        form = await request.form()
        payload = {key: value for key, value in form.items()}
    payment = db.scalar(select(Payment).where(Payment.provider_trade_no == trade_no))
    if payment is None:
        raise NotFoundError("支付记录不存在")
    provider = get_payment_provider()
    if not provider.verify_callback(payload):
        raise BizError("回调验签失败", code=401, status_code=401)
    payment.callback_payload = payload
    if payment.status == "PENDING":
        order = db.get(Order, payment.order_id)
        try:
            confirm_paid_order(db, order, payment, get_payment_provider())
        except BizError:
            # 已自动退款等场景：仍向支付宝返回成功，避免重复通知
            db.commit()
    else:
        db.commit()
    return Response(content="success", media_type="text/plain")
