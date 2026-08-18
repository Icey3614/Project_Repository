from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.session import MovieSession
from app.models.ticket import Ticket
from app.models.transfer_record import TransferRecord
from app.models.user import User
from app.schemas.common import Envelope
from app.schemas.transfer import TransferOut

router = APIRouter()


@router.get("", response_model=Envelope[list[TransferOut]])
def list_my_transfers(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    records = db.scalars(
        select(TransferRecord)
        .where(TransferRecord.from_user_id == user.id)
        .options(
            selectinload(TransferRecord.ticket).selectinload(Ticket.seat),
            selectinload(TransferRecord.ticket).selectinload(Ticket.session).selectinload(MovieSession.movie),
        )
        .order_by(TransferRecord.created_at.desc())
    ).all()
    recipient_ids = {r.to_user_id for r in records}
    usernames = {}
    if recipient_ids:
        usernames = {
            u.id: u.username
            for u in db.scalars(select(User).where(User.id.in_(recipient_ids))).all()
        }
    return Envelope(
        data=[
            TransferOut(
                id=r.id,
                ticket_id=r.ticket_id,
                to_user_id=r.to_user_id,
                to_username=usernames.get(r.to_user_id, ""),
                seat_no=r.ticket.seat.seat_no,
                movie_title=r.ticket.session.movie.title,
                start_at=r.ticket.session.start_at,
                created_at=r.created_at,
            )
            for r in records
        ]
    )
