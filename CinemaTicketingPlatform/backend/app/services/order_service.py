from datetime import datetime, timedelta
from decimal import Decimal
import random

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.exceptions import BizError, NotFoundError
from app.models.order import Order
from app.models.session import MovieSession
from app.models.session_seat import SessionSeat
from app.models.ticket import Ticket
from app.models.user import User
from app.services.session_service import payment_cutoff

ORDER_TTL_MINUTES = 20


def _generate_order_no() -> str:
    return f"C{datetime.now():%Y%m%d%H%M%S}{random.randint(1000, 9999)}"


def release_expired_locks(db: Session, session_id: int | None = None) -> int:
    """释放所有已过期（超过 20 分钟）的座位锁，并同步票与订单状态。"""
    now = datetime.now()
    seat_stmt = (
        update(SessionSeat)
        .where(
            SessionSeat.status == "LOCKED",
            SessionSeat.lock_expires_at.is_not(None),
            SessionSeat.lock_expires_at < now,
        )
        .values(status="AVAILABLE", lock_order_id=None, lock_expires_at=None)
    )
    if session_id is not None:
        seat_stmt = seat_stmt.where(SessionSeat.session_id == session_id)
    released = db.execute(seat_stmt).rowcount or 0

    ticket_stmt = (
        update(Ticket)
        .where(
            Ticket.status == "PENDING_PAYMENT",
            Ticket.expires_at.is_not(None),
            Ticket.expires_at < now,
        )
        .values(status="EXPIRED")
    )
    if session_id is not None:
        ticket_stmt = ticket_stmt.where(Ticket.session_id == session_id)
    db.execute(ticket_stmt)

    pending_order_ids = set(
        db.scalars(select(Order.id).where(Order.status == "PENDING_PAYMENT")).all()
    )
    if pending_order_ids:
        alive = set(
            db.scalars(
                select(Ticket.order_id).where(
                    Ticket.order_id.in_(pending_order_ids),
                    Ticket.status == "PENDING_PAYMENT",
                )
            ).all()
        )
        expired_ids = pending_order_ids - alive
        if expired_ids:
            db.execute(update(Order).where(Order.id.in_(expired_ids)).values(status="EXPIRED"))
    return released


def release_at_cutoff(db: Session) -> int:
    """停售/支付截止到点：强制释放该场次所有未付款票，锁定售卖状态。"""
    now = datetime.now()
    released = 0
    for session in db.scalars(select(MovieSession)).all():
        if now >= payment_cutoff(session):
            order_ids = list(
                db.scalars(
                    select(Ticket.order_id).where(
                        Ticket.session_id == session.id,
                        Ticket.status == "PENDING_PAYMENT",
                    )
                ).all()
            )
            db.execute(
                update(SessionSeat)
                .where(
                    SessionSeat.session_id == session.id,
                    SessionSeat.status == "LOCKED",
                )
                .values(status="AVAILABLE", lock_order_id=None, lock_expires_at=None)
            )
            result = db.execute(
                update(Ticket)
                .where(
                    Ticket.session_id == session.id,
                    Ticket.status == "PENDING_PAYMENT",
                )
                .values(status="EXPIRED")
            )
            released += result.rowcount or 0
            if order_ids:
                db.execute(
                    update(Order)
                    .where(Order.id.in_(order_ids), Order.status == "PENDING_PAYMENT")
                    .values(status="EXPIRED")
                )
    return released


def auto_checkin(db: Session) -> int:
    """开场自动核销兜底：已到开场时间的场次，所有待使用票标记为已使用。"""
    now = datetime.now()
    count = 0
    for session in db.scalars(select(MovieSession).where(MovieSession.start_at <= now)).all():
        result = db.execute(
            update(Ticket)
            .where(Ticket.session_id == session.id, Ticket.status == "UNUSED")
            .values(status="USED", checked_in_at=now, checked_in_by=None)
        )
        count += result.rowcount or 0
    return count


def create_order(user: User, payload, db: Session) -> Order:
    session = db.get(MovieSession, payload.session_id)
    if session is None:
        raise NotFoundError("场次不存在")

    now = datetime.now()
    if now < session.sale_open_at:
        raise BizError("尚未开售")
    if now >= payment_cutoff(session):
        raise BizError("已停止售票")
    if len(payload.seat_ids) > 3:
        raise BizError("单次最多购买 3 张票")
    if len(payload.seat_ids) != len(set(payload.seat_ids)):
        raise BizError("座位不可重复")

    # 锁定用户行，串行化同一用户的并发下单，保证 3 张上限
    db.execute(select(User).where(User.id == user.id).with_for_update())
    active_count = len(
        db.scalars(
            select(Ticket).where(
                Ticket.owner_user_id == user.id,
                Ticket.status.in_(["PENDING_PAYMENT", "UNUSED"]),
            )
        ).all()
    )
    if active_count + len(payload.seat_ids) > 3:
        raise BizError("每人最多同时持有 3 张活跃票（待支付 + 待使用）")

    release_expired_locks(db, session.id)

    seats = db.execute(
        select(SessionSeat)
        .where(SessionSeat.session_id == session.id, SessionSeat.id.in_(payload.seat_ids))
        .with_for_update()
    ).scalars().all()
    if len(seats) != len(payload.seat_ids):
        raise BizError("请求中包含无效座位")
    for seat in seats:
        if seat.status != "AVAILABLE":
            raise BizError(f"座位 {seat.seat_no} 已被锁定或售出")

    order = Order(
        order_no=_generate_order_no(),
        user_id=user.id,
        session_id=session.id,
        status="PENDING_PAYMENT",
        total_amount=sum((seat.price for seat in seats), Decimal("0.00")),
    )
    db.add(order)
    db.flush()

    expires_at = now + timedelta(minutes=ORDER_TTL_MINUTES)
    for seat in seats:
        seat.status = "LOCKED"
        seat.lock_order_id = order.id
        seat.lock_expires_at = expires_at
        db.add(
            Ticket(
                order_id=order.id,
                session_id=session.id,
                session_seat_id=seat.id,
                purchaser_user_id=user.id,
                owner_user_id=user.id,
                origin="SELF",
                transfer_count=0,
                status="PENDING_PAYMENT",
                price=seat.price,
                expires_at=expires_at,
            )
        )
    db.commit()
    db.refresh(order)
    return order


def cancel_order(user: User, order_id: int, db: Session) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise NotFoundError("订单不存在")
    if order.user_id != user.id:
        raise PermissionDenied()
    if order.status != "PENDING_PAYMENT":
        raise BizError("订单状态不允许取消")

    tickets = db.scalars(
        select(Ticket).where(Ticket.order_id == order.id)
    ).all()
    for t in tickets:
        if t.status == "PENDING_PAYMENT":
            t.status = "EXPIRED"
            t.expires_at = None
            seat = db.get(SessionSeat, t.session_seat_id)
            if seat is not None and seat.status == "LOCKED":
                seat.status = "AVAILABLE"
                seat.lock_order_id = None
                seat.lock_expires_at = None
    order.status = "CANCELLED"
    db.commit()
    db.refresh(order)
    return order
