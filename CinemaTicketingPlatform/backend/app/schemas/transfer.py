from datetime import datetime

from pydantic import BaseModel, Field


class TransferCreate(BaseModel):
    to_user_id: int = Field(gt=0)


class TransferOut(BaseModel):
    id: int
    ticket_id: int
    to_user_id: int
    to_username: str
    seat_no: str
    movie_title: str
    start_at: datetime
    created_at: datetime
