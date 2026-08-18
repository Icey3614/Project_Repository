from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BizError, NotFoundError, PermissionDenied
from app.models.session import MovieSession
from app.models.ticket import Ticket
from app.models.transfer_record import TransferRecord
from app.models.user import User

TRANSFER_FREEZE_MINUTES = 10


def transfer_ticket(user: User, ticket_id: int, to_user_id: int, db: Session) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise NotFoundError("票不存在")
    if ticket.owner_user_id != user.id:
        raise PermissionDenied()
    if ticket.status != "UNUSED":
        raise BizError("仅待使用状态的票可转赠")
    if ticket.origin != "SELF" or ticket.transfer_count != 0:
        raise BizError("受赠票不可再次转赠")
    if to_user_id == user.id:
        raise BizError("不能转赠给自己")
    recipient = db.get(User, to_user_id)
    if recipient is None:
        raise NotFoundError("目标用户不存在")
    session = db.get(MovieSession, ticket.session_id)
    if datetime.now() >= session.start_at - timedelta(minutes=TRANSFER_FREEZE_MINUTES):
        raise BizError("开场前 10 分钟起不可转赠")

    active = len(
        db.scalars(
            select(Ticket).where(
                Ticket.owner_user_id == recipient.id,
                Ticket.status.in_(["PENDING_PAYMENT", "UNUSED"]),
            )
        ).all()
    )
    if active >= 3:
        raise BizError("对方已达 3 张活跃票上限")

    db.add(
        TransferRecord(
            ticket_id=ticket.id,
            from_user_id=user.id,
            to_user_id=recipient.id,
        )
    )
    ticket.owner_user_id = recipient.id
    ticket.origin = "GIFTED"
    ticket.transfer_count = 1
    db.commit()
    db.refresh(ticket)
    return ticket
