from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.refund_request import RefundRequest
from app.models.session import MovieSession
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.common import Envelope
from app.schemas.refund import RefundRequestOut

router = APIRouter()


def _to_out(req: RefundRequest) -> RefundRequestOut:
    return RefundRequestOut(
        id=req.id,
        ticket_id=req.ticket_id,
        user_id=req.user_id,
        seat_no=req.ticket.seat.seat_no,
        movie_title=req.ticket.session.movie.title,
        venue_name=req.ticket.session.venue.name,
        start_at=req.ticket.session.start_at,
        original_amount=req.original_amount,
        refund_amount=req.refund_amount,
        fee=req.fee,
        status=req.status,
        reason=req.reason,
        admin_id=req.admin_id,
        reviewed_at=req.reviewed_at,
        created_at=req.created_at,
    )


@router.get("", response_model=Envelope[list[RefundRequestOut]])
def list_my_refund_requests(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    requests = db.scalars(
        select(RefundRequest)
        .where(RefundRequest.user_id == user.id)
        .options(
            selectinload(RefundRequest.ticket).selectinload(Ticket.seat),
            selectinload(RefundRequest.ticket).selectinload(Ticket.session).selectinload(MovieSession.movie),
            selectinload(RefundRequest.ticket).selectinload(Ticket.session).selectinload(MovieSession.venue),
        )
        .order_by(RefundRequest.created_at.desc())
    ).all()
    return Envelope(data=[_to_out(r) for r in requests])
