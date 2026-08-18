from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BizError, NotFoundError, PermissionDenied
from app.models.order import Order
from app.models.payment import Payment
from app.models.session import MovieSession
from app.models.session_seat import SessionSeat
from app.models.ticket import Ticket
from app.models.user import User
from app.payments.factory import get_payment_provider
from app.services.session_service import payment_cutoff


def finalize_paid_order(db: Session, order: Order, tickets: list[Ticket]) -> None:
    """支付成功后的收尾：票转待使用、座位转已售、订单转已支付。"""
    now = datetime.now()
    amount = sum((t.price for t in tickets), Decimal("0.00"))
    for t in tickets:
        t.status = "UNUSED"
        t.expires_at = None
        seat = db.get(SessionSeat, t.session_seat_id)
        if seat is not None:
            seat.status = "SOLD"
            seat.lock_order_id = None
            seat.lock_expires_at = None
    order.status = "PAID"
    order.total_amount = amount
    order.paid_at = now


def confirm_paid_order(db: Session, order: Order, payment: Payment, provider) -> Order:
    """支付渠道确认已扣款后的统一收尾。

    - 全部票仍在锁定期：正常转已支付
    - 部分票已过期：只支付仍有效的票，多扣部分自动原路退回
    - 全部票已过期：自动全额原路退回，避免“钱扣了、票没有”
    """
    tickets = db.scalars(select(Ticket).where(Ticket.order_id == order.id)).all()
    remaining = [t for t in tickets if t.status == "PENDING_PAYMENT"]
    if not remaining:
        try:
            provider.refund(payment, payment.amount)
        except Exception:
            pass
        payment.status = "FAILED"
        db.commit()
        raise BizError("订单已超时，座位已释放，款项已自动原路退回")

    finalize_paid_order(db, order, remaining)
    actual = sum((t.price for t in remaining), Decimal("0.00"))
    if payment.amount > actual:
        try:
            provider.refund(payment, payment.amount - actual)
        except Exception:
            pass
    payment.status = "SUCCESS"
    payment.paid_at = datetime.now()
    db.commit()
    db.refresh(order)
    return order


def pay_order(user: User, order_id: int, db: Session) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise NotFoundError("订单不存在")
    if order.user_id != user.id:
        raise PermissionDenied()
    if order.status != "PENDING_PAYMENT":
        raise BizError("订单状态不允许支付")

    now = datetime.now()
    session = db.get(MovieSession, order.session_id)
    if session is not None and now >= payment_cutoff(session):
        raise BizError("已过支付截止时间")

    tickets = db.scalars(select(Ticket).where(Ticket.order_id == order.id)).all()
    for t in tickets:
        if t.status == "PENDING_PAYMENT" and t.expires_at is not None and t.expires_at < now:
            t.status = "EXPIRED"
            seat = db.get(SessionSeat, t.session_seat_id)
            if seat is not None and seat.status == "LOCKED":
                seat.status = "AVAILABLE"
                seat.lock_order_id = None
                seat.lock_expires_at = None

    remaining = [t for t in tickets if t.status == "PENDING_PAYMENT"]
    if not remaining:
        raise BizError("订单已超时，座位已释放")
    amount = sum((t.price for t in remaining), Decimal("0.00"))

    # 已有待确认的支付记录（跳转渠道）时直接复用，避免重复下单
    existing = db.scalar(
        select(Payment)
        .where(Payment.order_id == order.id, Payment.status == "PENDING")
        .order_by(Payment.id.desc())
    )
    if existing is not None:
        return order

    provider = get_payment_provider()
    try:
        result = provider.create_payment(order, amount, db)
    except Exception as exc:
        raise BizError(f"发起支付失败：{exc}")
    payment = Payment(
        order_id=order.id,
        user_id=user.id,
        amount=amount,
        method=provider.name,
        provider_trade_no=result.provider_trade_no,
        status="SUCCESS" if result.success else "PENDING",
        pay_url=result.pay_url,
    )
    db.add(payment)
    if result.success:
        payment.paid_at = now
        finalize_paid_order(db, order, remaining)
        db.commit()
        db.refresh(order)
        return order
    if result.pay_url:
        db.commit()
        db.refresh(order)
        return order
    db.commit()
    raise BizError(f"支付失败：{result.message}")


def sync_order_payment(user: User, order_id: int, db: Session) -> Order:
    """主动向支付渠道查询订单状态（本地开发无公网回调时的兜底）。"""
    order = db.get(Order, order_id)
    if order is None:
        raise NotFoundError("订单不存在")
    if order.user_id != user.id:
        raise PermissionDenied()
    if order.status == "PAID":
        return order
    payment = db.scalar(
        select(Payment)
        .where(Payment.order_id == order.id, Payment.status == "PENDING")
        .order_by(Payment.id.desc())
    )
    if payment is None:
        raise BizError("没有待确认的支付记录")
    provider = get_payment_provider()
    try:
        paid = provider.query_order(payment)
    except Exception as exc:
        raise BizError(f"支付状态查询失败：{exc}")
    if not paid:
        raise BizError("支付尚未完成，请稍后再试")
    return confirm_paid_order(db, order, payment, provider)
