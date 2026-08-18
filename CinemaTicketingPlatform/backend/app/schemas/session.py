from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    movie_id: int
    venue_id: int
    start_at: datetime
    sale_open_at: datetime
    sale_close_at: datetime
    base_price: Decimal = Field(gt=0, decimal_places=2)


class SessionUpdate(BaseModel):
    sale_open_at: datetime | None = None
    sale_close_at: datetime | None = None
    base_price: Decimal | None = Field(default=None, gt=0, decimal_places=2)


class SessionOut(BaseModel):
    id: int
    movie_id: int
    venue_id: int
    movie_title: str
    venue_name: str
    start_at: datetime
    end_at: datetime
    sale_open_at: datetime
    sale_close_at: datetime
    base_price: Decimal
    status: str
    remaining: int
    sold: int
    locked: int
    total_seats: int


class SessionSeatOut(BaseModel):
    id: int
    session_id: int
    row_no: int
    col_no: int
    seat_no: str
    price: Decimal
    status: str
