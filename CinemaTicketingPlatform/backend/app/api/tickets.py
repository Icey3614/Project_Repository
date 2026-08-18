from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.session import MovieSession
from app.models.ticket import Ticket
from app.models.transfer_record import TransferRecord
from app.models.user import User
from app.schemas.common import Envelope
from app.schemas.refund import RefundRequestCreate, RefundRequestOut
from app.schemas.ticket import TicketOut
from app.schemas.transfer import TransferCreate
from app.services.refund_service import create_refund_request
from app.services.transfer_service import transfer_ticket

router = APIRouter()


def _ticket_out(t: Ticket) -> TicketOut:
    return TicketOut(
        id=t.id,
        order_id=t.order_id,
        session_id=t.session_id,
        movie_title=t.session.movie.title,
        venue_name=t.session.venue.name,
        start_at=t.session.start_at,
        seat_no=t.seat.seat_no,
        row_no=t.seat.row_no,
        col_no=t.seat.col_no,
        price=t.price,
        status=t.status,
        origin=t.origin,
        transfer_count=t.transfer_count,
        expires_at=t.expires_at,
        checked_in_at=t.checked_in_at,
    )


@router.get("", response_model=Envelope[list[TicketOut]])
def list_my_tickets(
    tab: Optional[str] = Query(default=None, description="pending/unused/history"),
    status: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if tab == "pending":
        cond = and_(
            Ticket.owner_user_id == user.id,
            Ticket.status == "PENDING_PAYMENT",
        )
    elif tab == "unused":
        cond = and_(Ticket.owner_user_id == user.id, Ticket.status == "UNUSED")
    elif tab == "history":
        cond = or_(
            and_(
                Ticket.owner_user_id == user.id,
                Ticket.status.in_(["USED", "REFUNDED"]),
            ),
            and_(
                Ticket.purchaser_user_id == user.id,
                Ticket.owner_user_id != user.id,
            ),
        )
    else:
        cond = Ticket.owner_user_id == user.id
        if status:
            cond = and_(cond, Ticket.status == status)
    stmt = (
        select(Ticket)
        .where(cond)
        .options(
            selectinload(Ticket.seat),
            selectinload(Ticket.session).selectinload(MovieSession.movie),
            selectinload(Ticket.session).selectinload(MovieSession.venue),
        )
        .order_by(Ticket.created_at.desc())
    )
    tickets = db.scalars(stmt).all()

    transferred = [t for t in tickets if t.owner_user_id != t.purchaser_user_id]
    transferred_to: dict[int, str] = {}
    if transferred:
        records = db.scalars(
            select(TransferRecord).where(
                TransferRecord.ticket_id.in_([t.id for t in transferred]),
                TransferRecord.from_user_id == user.id,
            )
        ).all()
        recipient_ids = {r.to_user_id for r in records}
        usernames = {}
        if recipient_ids:
            usernames = {
                u.id: u.username
                for u in db.scalars(select(User).where(User.id.in_(recipient_ids))).all()
            }
        for r in records:
            transferred_to[r.ticket_id] = usernames.get(r.to_user_id, "")

    items = []
    for t in tickets:
        out = _ticket_out(t)
        out.transferred_out = t.owner_user_id != t.purchaser_user_id
        out.transferred_to = transferred_to.get(t.id)
        items.append(out)
    return Envelope(data=items)


@router.post("/{ticket_id}/transfer", response_model=Envelope[TicketOut])
def transfer_ticket_endpoint(
    ticket_id: int,
    payload: TransferCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    transfer_ticket(user, ticket_id, payload.to_user_id, db)
    ticket = db.scalar(
        select(Ticket)
        .where(Ticket.id == ticket_id)
        .options(
            selectinload(Ticket.seat),
            selectinload(Ticket.session).selectinload(MovieSession.movie),
            selectinload(Ticket.session).selectinload(MovieSession.venue),
        )
    )
    return Envelope(data=_ticket_out(ticket))


@router.post(
    "/{ticket_id}/refund-request",
    response_model=Envelope[RefundRequestOut],
    status_code=201,
)
def create_refund_request_endpoint(
    ticket_id: int,
    payload: RefundRequestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    request = create_refund_request(user, ticket_id, payload.reason, db)
    return Envelope(
        data=RefundRequestOut(
            id=request.id,
            ticket_id=request.ticket_id,
            user_id=request.user_id,
            seat_no=request.ticket.seat.seat_no,
            movie_title=request.ticket.session.movie.title,
            venue_name=request.ticket.session.venue.name,
            start_at=request.ticket.session.start_at,
            original_amount=request.original_amount,
            refund_amount=request.refund_amount,
            fee=request.fee,
            status=request.status,
            reason=request.reason,
            admin_id=request.admin_id,
            reviewed_at=request.reviewed_at,
            created_at=request.created_at,
        )
    )
