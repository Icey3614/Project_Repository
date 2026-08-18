from datetime import date, datetime, time, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.session import MovieSession
from app.models.session_seat import SessionSeat
from app.models.user import User
from app.schemas.common import Envelope, Page
from app.schemas.session import (
    SessionCreate,
    SessionOut,
    SessionSeatOut,
    SessionUpdate,
)
from app.services.order_service import release_expired_locks
from app.services.session_service import (
    create_session,
    delete_session,
    session_status,
    update_session,
)

router = APIRouter()


def _seat_counts(db: Session, session_ids: list[int]) -> dict[tuple[int, str], int]:
    rows = db.execute(
        select(SessionSeat.session_id, SessionSeat.status, func.count(SessionSeat.id))
        .where(SessionSeat.session_id.in_(session_ids))
        .group_by(SessionSeat.session_id, SessionSeat.status)
    ).all()
    return {(sid, status): count for sid, status, count in rows}


def _to_out(session: MovieSession, counts: dict[tuple[int, str], int], now: datetime) -> SessionOut:
    available = counts.get((session.id, "AVAILABLE"), 0)
    locked = counts.get((session.id, "LOCKED"), 0)
    sold = counts.get((session.id, "SOLD"), 0)
    return SessionOut(
        id=session.id,
        movie_id=session.movie_id,
        venue_id=session.venue_id,
        movie_title=session.movie.title,
        venue_name=session.venue.name,
        start_at=session.start_at,
        end_at=session.end_at,
        sale_open_at=session.sale_open_at,
        sale_close_at=session.sale_close_at,
        base_price=session.base_price,
        status=session_status(session, now, available),
        remaining=available,
        sold=sold,
        locked=locked,
        total_seats=available + locked + sold,
    )


@router.get("", response_model=Envelope[Page[SessionOut]])
def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    movie_id: Optional[int] = None,
    venue_id: Optional[int] = None,
    on_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    release_expired_locks(db)
    base = select(MovieSession)
    if movie_id is not None:
        base = base.where(MovieSession.movie_id == movie_id)
    if venue_id is not None:
        base = base.where(MovieSession.venue_id == venue_id)
    if on_date is not None:
        day_start = datetime.combine(on_date, time.min)
        day_end = datetime.combine(on_date + timedelta(days=1), time.min)
        base = base.where(MovieSession.start_at >= day_start, MovieSession.start_at < day_end)

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    sessions = db.scalars(
        base.order_by(MovieSession.start_at)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    counts = _seat_counts(db, [s.id for s in sessions]) if sessions else {}
    now = datetime.now()
    return Envelope(
        data=Page(
            items=[_to_out(s, counts, now) for s in sessions],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/{session_id}", response_model=Envelope[SessionOut])
def get_session(session_id: int, db: Session = Depends(get_db)):
    release_expired_locks(db, session_id)
    session = db.get(MovieSession, session_id)
    if session is None:
        raise NotFoundError("场次不存在")
    counts = _seat_counts(db, [session.id])
    return Envelope(data=_to_out(session, counts, datetime.now()))


@router.get("/{session_id}/seats", response_model=Envelope[list[SessionSeatOut]])
def get_session_seats(session_id: int, db: Session = Depends(get_db)):
    release_expired_locks(db, session_id)
    session = db.get(MovieSession, session_id)
    if session is None:
        raise NotFoundError("场次不存在")
    seats = db.scalars(
        select(SessionSeat)
        .where(SessionSeat.session_id == session_id)
        .order_by(SessionSeat.row_no, SessionSeat.col_no)
    ).all()
    return Envelope(
        data=[
            SessionSeatOut(
                id=s.id,
                session_id=s.session_id,
                row_no=s.row_no,
                col_no=s.col_no,
                seat_no=s.seat_no,
                price=s.price,
                status=s.status,
            )
            for s in seats
        ]
    )


@router.post("", response_model=Envelope[SessionOut], status_code=201)
def create_session_endpoint(
    payload: SessionCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    session = create_session(payload, db)
    counts = _seat_counts(db, [session.id])
    return Envelope(data=_to_out(session, counts, datetime.now()))


@router.put("/{session_id}", response_model=Envelope[SessionOut])
def update_session_endpoint(
    session_id: int,
    payload: SessionUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    session = db.get(MovieSession, session_id)
    if session is None:
        raise NotFoundError("场次不存在")
    session = update_session(payload, db, session)
    counts = _seat_counts(db, [session.id])
    return Envelope(data=_to_out(session, counts, datetime.now()))


@router.delete("/{session_id}", response_model=Envelope[None])
def delete_session_endpoint(
    session_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    session = db.get(MovieSession, session_id)
    if session is None:
        raise NotFoundError("场次不存在")
    delete_session(db, session)
    return Envelope(data=None)
