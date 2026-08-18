from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.payment import PaymentOut
from app.schemas.ticket import TicketOut


class OrderCreate(BaseModel):
    session_id: int
    seat_ids: list[int] = Field(min_length=1, max_length=3)


class OrderOut(BaseModel):
    id: int
    order_no: str
    session_id: int
    status: str
    total_amount: Decimal
    created_at: datetime
    paid_at: datetime | None
    tickets: list[TicketOut]
    payments: list[PaymentOut] = []
