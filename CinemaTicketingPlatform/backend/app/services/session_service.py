from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import BizError, NotFoundError
from app.models.movie import Movie
from app.models.order import Order
from app.models.session import MovieSession
from app.models.session_seat import SessionSeat
from app.models.venue import Venue
from app.models.venue_seat import VenueSeat

BUFFER_MINUTES = 30
PAYMENT_CUTOFF_MINUTES = 20


def payment_cutoff(session: MovieSession) -> datetime:
    """支付截止 = min(停售时间, 开场前 20 分钟)。"""
    return min(
        session.sale_close_at,
        session.start_at - timedelta(minutes=PAYMENT_CUTOFF_MINUTES),
    )


def session_status(session: MovieSession, now: datetime | None = None, remaining: int | None = None) -> str:
    now = now or datetime.now()
    if now >= session.start_at:
        return "ENDED"
    if now < session.sale_open_at:
        return "SCHEDULED"
    if now >= payment_cutoff(session):
        return "STOPPED"
    if remaining == 0:
        return "SOLD_OUT"
    return "SELLING"


def create_session(payload, db: Session) -> MovieSession:
    movie = db.get(Movie, payload.movie_id)
    if movie is None:
        raise NotFoundError("电影不存在")
    venue = db.get(Venue, payload.venue_id)
    if venue is None:
        raise NotFoundError("场馆不存在")

    start = payload.start_at
    end = start + timedelta(minutes=movie.duration_min)
    if payload.sale_open_at >= payload.sale_close_at:
        raise BizError("开售时间必须早于停售时间")
    if payload.sale_close_at >= start:
        raise BizError("停售时间必须早于电影开场")
    if payload.sale_open_at >= start:
        raise BizError("开售时间必须早于电影开场")

    conflict = db.scalar(
        select(func.count())
        .select_from(MovieSession)
        .where(
            MovieSession.venue_id == venue.id,
            MovieSession.start_at < end + timedelta(minutes=BUFFER_MINUTES),
            MovieSession.end_at > start - timedelta(minutes=BUFFER_MINUTES),
        )
    )
    if conflict:
        raise BizError("该时段与已有场次冲突（含 30 分钟清扫缓冲）", code=409, status_code=409)

    session = MovieSession(
        movie_id=movie.id,
        venue_id=venue.id,
        start_at=start,
        end_at=end,
        sale_open_at=payload.sale_open_at,
        sale_close_at=payload.sale_close_at,
        base_price=payload.base_price,
    )
    db.add(session)
    db.flush()

    template_seats = db.scalars(
        select(VenueSeat).where(VenueSeat.venue_id == venue.id)
    ).all()
    for ts in template_seats:
        db.add(
            SessionSeat(
                session_id=session.id,
                row_no=ts.row_no,
                col_no=ts.col_no,
                seat_no=ts.seat_no,
                price=payload.base_price,
                status="AVAILABLE" if ts.enabled else "DISABLED",
            )
        )
    db.commit()
    db.refresh(session)
    return session


def has_blocking_orders(db: Session, session: MovieSession) -> bool:
    count = db.scalar(
        select(func.count())
        .select_from(Order)
        .where(
            Order.session_id == session.id,
            Order.status.in_(["PENDING_PAYMENT", "PAID"]),
        )
    )
    return bool(count)


def update_session(payload, db: Session, session: MovieSession) -> MovieSession:
    if session.start_at <= datetime.now():
        raise BizError("已开始的场次不可修改")
    if has_blocking_orders(db, session):
        raise BizError("已有订单的场次禁止修改")
    new_open = payload.sale_open_at if payload.sale_open_at is not None else session.sale_open_at
    new_close = payload.sale_close_at if payload.sale_close_at is not None else session.sale_close_at
    if new_open >= new_close:
        raise BizError("开售时间必须早于停售时间")
    if new_close >= session.start_at:
        raise BizError("停售时间必须早于电影开场")
    if new_open >= session.start_at:
        raise BizError("开售时间必须早于电影开场")
    if payload.sale_open_at is not None:
        session.sale_open_at = payload.sale_open_at
    if payload.sale_close_at is not None:
        session.sale_close_at = payload.sale_close_at
    if payload.base_price is not None:
        session.base_price = payload.base_price
    db.commit()
    db.refresh(session)
    return session


def delete_session(db: Session, session: MovieSession) -> None:
    if session.start_at <= datetime.now():
        raise BizError("已开始的场次不可删除")
    if has_blocking_orders(db, session):
        raise BizError("已有订单的场次禁止删除")
    db.delete(session)
    db.commit()
