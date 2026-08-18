from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_current_user
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.order import Order
from app.models.payment import Payment
from app.models.session import MovieSession
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.common import Envelope, Page
from app.schemas.order import OrderCreate, OrderOut
from app.schemas.payment import PaymentOut
from app.schemas.ticket import TicketOut
from app.services.order_service import cancel_order, create_order
from app.services.payment_service import pay_order, sync_order_payment

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


def _order_out(order: Order) -> OrderOut:
    return OrderOut(
        id=order.id,
        order_no=order.order_no,
        session_id=order.session_id,
        status=order.status,
        total_amount=order.total_amount,
        created_at=order.created_at,
        paid_at=order.paid_at,
        tickets=[_ticket_out(t) for t in order.tickets],
        payments=[
            PaymentOut(
                id=p.id,
                order_id=p.order_id,
                method=p.method,
                provider_trade_no=p.provider_trade_no,
                status=p.status,
                amount=p.amount,
                pay_url=p.pay_url,
                created_at=p.created_at,
                paid_at=p.paid_at,
            )
            for p in order.payments
        ],
    )


def _load_order(db: Session, order_id: int, user: User) -> Order:
    order = db.scalar(
        select(Order)
        .where(Order.id == order_id, Order.user_id == user.id)
        .options(
            selectinload(Order.tickets).selectinload(Ticket.seat),
            selectinload(Order.tickets).selectinload(Ticket.session).selectinload(MovieSession.movie),
            selectinload(Order.tickets).selectinload(Ticket.session).selectinload(MovieSession.venue),
            selectinload(Order.payments),
        )
    )
    if order is None:
        raise NotFoundError("订单不存在")
    return order


@router.post("", response_model=Envelope[OrderOut], status_code=201)
def create_order_endpoint(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    order = create_order(user, payload, db)
    return Envelope(data=_order_out(_load_order(db, order.id, user)))


@router.get("", response_model=Envelope[Page[OrderOut]])
def list_my_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    base = select(Order).where(Order.user_id == user.id)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    orders = db.scalars(
        base.order_by(Order.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .options(
            selectinload(Order.tickets).selectinload(Ticket.seat),
            selectinload(Order.tickets).selectinload(Ticket.session).selectinload(MovieSession.movie),
            selectinload(Order.tickets).selectinload(Ticket.session).selectinload(MovieSession.venue),
            selectinload(Order.payments),
        )
    ).all()
    return Envelope(
        data=Page(
            items=[_order_out(o) for o in orders],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/{order_id}", response_model=Envelope[OrderOut])
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return Envelope(data=_order_out(_load_order(db, order_id, user)))


@router.post("/{order_id}/pay", response_model=Envelope[OrderOut])
def pay_order_endpoint(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pay_order(user, order_id, db)
    return Envelope(data=_order_out(_load_order(db, order_id, user)))


@router.post("/{order_id}/sync-payment", response_model=Envelope[OrderOut])
def sync_payment_endpoint(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    order = sync_order_payment(user, order_id, db)
    return Envelope(data=_order_out(_load_order(db, order_id, user)))


@router.post("/{order_id}/cancel", response_model=Envelope[OrderOut])
def cancel_order_endpoint(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cancel_order(user, order_id, db)
    return Envelope(data=_order_out(_load_order(db, order_id, user)))
