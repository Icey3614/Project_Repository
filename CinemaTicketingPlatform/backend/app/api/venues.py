from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.core.exceptions import BizError, NotFoundError
from app.db.session import get_db
from app.models.session import MovieSession
from app.models.user import User
from app.models.venue import Venue
from app.models.venue_seat import VenueSeat
from app.schemas.common import Envelope
from app.schemas.venue import (
    VenueCreate,
    VenueOut,
    VenueSeatBatchUpdate,
    VenueSeatOut,
    VenueUpdate,
)

router = APIRouter()


@router.get("", response_model=Envelope[list[VenueOut]])
def list_venues(db: Session = Depends(get_db)):
    venues = db.scalars(select(Venue).order_by(Venue.id.desc())).all()
    return Envelope(data=[VenueOut.model_validate(v) for v in venues])


@router.get("/{venue_id}", response_model=Envelope[VenueOut])
def get_venue(venue_id: int, db: Session = Depends(get_db)):
    venue = db.get(Venue, venue_id)
    if venue is None:
        raise NotFoundError("场馆不存在")
    return Envelope(data=VenueOut.model_validate(venue))


@router.post("", response_model=Envelope[VenueOut], status_code=201)
def create_venue(
    payload: VenueCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    capacity = payload.capacity or payload.rows * payload.cols
    venue = Venue(
        name=payload.name,
        rows=payload.rows,
        cols=payload.cols,
        capacity=capacity,
        screen_pos=payload.screen_pos,
        exits=payload.exits,
        status="ACTIVE",
    )
    db.add(venue)
    db.flush()
    # 创建场馆时按行列自动生成座位模板，后续可在座位编辑器中调整
    for r in range(1, payload.rows + 1):
        for c in range(1, payload.cols + 1):
            db.add(
                VenueSeat(
                    venue_id=venue.id,
                    row_no=r,
                    col_no=c,
                    seat_no=f"{chr(64 + r)}{c}",
                    enabled=True,
                )
            )
    db.commit()
    db.refresh(venue)
    return Envelope(data=VenueOut.model_validate(venue))


@router.put("/{venue_id}", response_model=Envelope[VenueOut])
def update_venue(
    venue_id: int,
    payload: VenueUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    venue = db.get(Venue, venue_id)
    if venue is None:
        raise NotFoundError("场馆不存在")
    if db.scalar(
        select(MovieSession)
        .where(MovieSession.venue_id == venue_id, MovieSession.start_at > datetime.now())
        .limit(1)
    ):
        raise BizError("该场馆存在未来场次，禁止修改")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(venue, key, value)
    db.commit()
    db.refresh(venue)
    return Envelope(data=VenueOut.model_validate(venue))


@router.delete("/{venue_id}", response_model=Envelope[None])
def delete_venue(
    venue_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    venue = db.get(Venue, venue_id)
    if venue is None:
        raise NotFoundError("场馆不存在")
    if db.scalar(
        select(MovieSession)
        .where(MovieSession.venue_id == venue_id)
        .limit(1)
    ):
        raise BizError("该场馆已有场次，禁止删除")
    db.delete(venue)
    db.commit()
    return Envelope(data=None)


@router.get("/{venue_id}/seats", response_model=Envelope[list[VenueSeatOut]])
def list_venue_seats(venue_id: int, db: Session = Depends(get_db)):
    venue = db.get(Venue, venue_id)
    if venue is None:
        raise NotFoundError("场馆不存在")
    seats = db.scalars(
        select(VenueSeat)
        .where(VenueSeat.venue_id == venue_id)
        .order_by(VenueSeat.row_no, VenueSeat.col_no)
    ).all()
    return Envelope(data=[VenueSeatOut.model_validate(s) for s in seats])


@router.put("/{venue_id}/seats", response_model=Envelope[None])
def update_venue_seats(
    venue_id: int,
    payload: VenueSeatBatchUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    venue = db.get(Venue, venue_id)
    if venue is None:
        raise NotFoundError("场馆不存在")
    ids = [s.id for s in payload.seats]
    if len(ids) != len(set(ids)):
        raise BizError("请求中包含重复的座位")
    existing = db.scalars(
        select(VenueSeat).where(VenueSeat.venue_id == venue_id, VenueSeat.id.in_(ids))
    ).all()
    if len(existing) != len(ids):
        raise BizError("请求中包含不属于该场馆的座位")
    by_id = {seat.id: seat for seat in existing}
    for item in payload.seats:
        by_id[item.id].enabled = item.enabled
    db.commit()
    return Envelope(data=None)
