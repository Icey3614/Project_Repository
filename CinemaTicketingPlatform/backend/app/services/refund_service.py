from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BizError, NotFoundError, PermissionDenied
from app.models.payment import Payment
from app.models.refund_request import RefundRequest
from app.models.session import MovieSession
from app.models.session_seat import SessionSeat
from app.models.ticket import Ticket
from app.models.user import User
from app.payments.factory import get_payment_provider
from app.services.session_service import payment_cutoff

REFUND_FREEZE_MINUTES = 10
REFUND_FEE_RATE = Decimal("0.10")


def freeze_time(session: MovieSession) -> datetime:
    """开场前 10 分钟：票冻结，不可转赠、不可退款。"""
    return session.start_at - timedelta(minutes=REFUND_FREEZE_MINUTES)


def create_refund_request(user: User, ticket_id: int, reason: str | None, db: Session) -> RefundRequest:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise NotFoundError("票不存在")
    if ticket.owner_user_id != user.id:
        raise PermissionDenied()
    if ticket.origin != "SELF":
        raise BizError("受赠票不可退款")
    if ticket.status != "UNUSED":
        raise BizError("仅待使用状态的票可申请退款")
    session = db.get(MovieSession, ticket.session_id)
    if datetime.now() >= freeze_time(session):
        raise BizError("开场前 10 分钟起不可退款")
    existing = db.scalar(
        select(RefundRequest).where(
            RefundRequest.ticket_id == ticket.id,
            RefundRequest.status == "PENDING",
        )
    )
    if existing is not None:
        raise BizError("该票已有待审核的退款申请")

    price = ticket.price
    refund_amount = (price * (Decimal("1") - REFUND_FEE_RATE)).quantize(Decimal("0.01"))
    fee = (price - refund_amount).quantize(Decimal("0.01"))
    request = RefundRequest(
        ticket_id=ticket.id,
        user_id=user.id,
        original_amount=price,
        refund_amount=refund_amount,
        fee=fee,
        status="PENDING",
        reason=reason,
    )
    ticket.status = "REFUND_APPLIED"
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def approve_refund(request_id: int, admin: User, db: Session) -> RefundRequest:
    request = db.get(RefundRequest, request_id)
    if request is None:
        raise NotFoundError("退款申请不存在")
    if request.status != "PENDING":
        raise BizError("该申请已处理")

    now = datetime.now()
    ticket = db.get(Ticket, request.ticket_id)
    session = db.get(MovieSession, ticket.session_id)
    seat = db.get(SessionSeat, ticket.session_seat_id)

    if now < payment_cutoff(session):
        seat.status = "AVAILABLE"
    else:
        seat.status = "DISABLED"
    seat.lock_order_id = None
    seat.lock_expires_at = None
    ticket.status = "REFUNDED"

    payment = db.scalar(
        select(Payment)
        .where(Payment.order_id == ticket.order_id, Payment.status == "SUCCESS")
        .order_by(Payment.id.desc())
    )
    if payment is not None:
        get_payment_provider().refund(payment, request.refund_amount)

    request.status = "APPROVED"
    request.admin_id = admin.id
    request.reviewed_at = now
    db.commit()
    db.refresh(request)
    return request


def reject_refund(request_id: int, admin: User, db: Session) -> RefundRequest:
    request = db.get(RefundRequest, request_id)
    if request is None:
        raise NotFoundError("退款申请不存在")
    if request.status != "PENDING":
        raise BizError("该申请已处理")
    ticket = db.get(Ticket, request.ticket_id)
    ticket.status = "UNUSED"
    request.status = "REJECTED"
    request.admin_id = admin.id
    request.reviewed_at = datetime.now()
    db.commit()
    db.refresh(request)
    return request
