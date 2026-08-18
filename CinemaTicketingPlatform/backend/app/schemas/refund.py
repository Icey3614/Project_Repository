from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class RefundRequestCreate(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class RefundRequestOut(BaseModel):
    id: int
    ticket_id: int
    user_id: int
    seat_no: str
    movie_title: str
    venue_name: str
    start_at: datetime
    original_amount: Decimal
    refund_amount: Decimal
    fee: Decimal
    status: str
    reason: str | None
    admin_id: int | None
    reviewed_at: datetime | None
    created_at: datetime
