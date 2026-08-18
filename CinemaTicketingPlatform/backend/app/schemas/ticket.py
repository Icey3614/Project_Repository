from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class TicketOut(BaseModel):
    id: int
    order_id: int
    session_id: int
    movie_title: str
    venue_name: str
    start_at: datetime
    seat_no: str
    row_no: int
    col_no: int
    price: Decimal
    status: str
    origin: str
    transfer_count: int
    expires_at: datetime | None
    checked_in_at: datetime | None
    transferred_out: bool = False
    transferred_to: str | None = None


class TicketAdminOut(BaseModel):
    id: int
    seat_no: str
    price: Decimal
    status: str
    origin: str
    owner_username: str
    purchaser_username: str
    checked_in_at: datetime | None
