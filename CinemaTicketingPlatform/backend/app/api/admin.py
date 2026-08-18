from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.deps import require_admin
from app.core.exceptions import BizError, NotFoundError
from app.db.session import get_db
from app.models.refund_request import RefundRequest
from app.models.session import MovieSession
from app.models.session_seat import SessionSeat
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.common import Envelope
from app.schemas.refund import RefundRequestOut
from app.schemas.ticket import TicketAdminOut
from app.services.refund_service import approve_refund, reject_refund

router = APIRouter()


@router.get("/sessions/{session_id}/tickets", response_model=Envelope[list[TicketAdminOut]])
def list_session_tickets(
    session_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    session = db.get(MovieSession, session_id)
    if session is None:
        raise NotFoundError("场次不存在")
    tickets = db.scalars(
        select(Ticket).where(Ticket.session_id == session_id).order_by(Ticket.id)
    ).all()
    user_ids = {t.owner_user_id for t in tickets} | {t.purchaser_user_id for t in tickets}
    usernames = {}
    if user_ids:
        usernames = {
            u.id: u.username
            for u in db.scalars(select(User).where(User.id.in_(user_ids))).all()
        }
    return Envelope(
        data=[
            TicketAdminOut(
                id=t.id,
                seat_no=db.get(SessionSeat, t.session_seat_id).seat_no,
                price=t.price,
                status=t.status,
                origin=t.origin,
                owner_username=usernames.get(t.owner_user_id, ""),
                purchaser_username=usernames.get(t.purchaser_user_id, ""),
                checked_in_at=t.checked_in_at,
            )
            for t in tickets
        ]
    )


def _refund_out(req: RefundRequest) -> RefundRequestOut:
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


def _refund_query() -> select:
    return select(RefundRequest).options(
        selectinload(RefundRequest.ticket).selectinload(Ticket.seat),
        selectinload(RefundRequest.ticket).selectinload(Ticket.session).selectinload(MovieSession.movie),
        selectinload(RefundRequest.ticket).selectinload(Ticket.session).selectinload(MovieSession.venue),
    )


@router.get("/refund-requests", response_model=Envelope[list[RefundRequestOut]])
def list_refund_requests(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    stmt = _refund_query().order_by(RefundRequest.created_at.desc())
    if status:
        stmt = stmt.where(RefundRequest.status == status)
    requests = db.scalars(stmt).all()
    return Envelope(data=[_refund_out(r) for r in requests])


@router.post("/refund-requests/{request_id}/approve", response_model=Envelope[RefundRequestOut])
def approve_refund_endpoint(
    request_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    approve_refund(request_id, admin, db)
    request = db.scalar(_refund_query().where(RefundRequest.id == request_id))
    return Envelope(data=_refund_out(request))


@router.post("/refund-requests/{request_id}/reject", response_model=Envelope[RefundRequestOut])
def reject_refund_endpoint(
    request_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    reject_refund(request_id, admin, db)
    request = db.scalar(_refund_query().where(RefundRequest.id == request_id))
    return Envelope(data=_refund_out(request))


@router.post("/sessions/{session_id}/checkin", response_model=Envelope[dict])
def checkin_session(
    session_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    session = db.get(MovieSession, session_id)
    if session is None:
        raise NotFoundError("场次不存在")
    from datetime import datetime

    tickets = db.scalars(
        select(Ticket).where(Ticket.session_id == session_id, Ticket.status == "UNUSED")
    ).all()
    now = datetime.now()
    for t in tickets:
        t.status = "USED"
        t.checked_in_at = now
        t.checked_in_by = admin.id
    db.commit()
    return Envelope(data={"checked_in": len(tickets)})


@router.post("/tickets/{ticket_id}/checkin", response_model=Envelope[dict])
def checkin_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise NotFoundError("票不存在")
    if ticket.status != "UNUSED":
        raise BizError("仅待使用状态的票可核销")
    from datetime import datetime

    ticket.status = "USED"
    ticket.checked_in_at = datetime.now()
    ticket.checked_in_by = admin.id
    db.commit()
    return Envelope(data={"checked_in": 1})
