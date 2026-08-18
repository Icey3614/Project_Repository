from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class VenueCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    rows: int = Field(ge=1, le=100)
    cols: int = Field(ge=1, le=100)
    capacity: int | None = Field(default=None, ge=1)
    screen_pos: dict | None = None
    exits: list | None = None


class VenueUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    screen_pos: dict | None = None
    exits: list | None = None
    status: str | None = Field(default=None, max_length=20)


class VenueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    rows: int
    cols: int
    capacity: int
    screen_pos: dict | None
    exits: list | None
    status: str
    created_at: datetime


class VenueSeatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    venue_id: int
    row_no: int
    col_no: int
    seat_no: str
    enabled: bool


class VenueSeatUpdateItem(BaseModel):
    id: int
    enabled: bool


class VenueSeatBatchUpdate(BaseModel):
    seats: list[VenueSeatUpdateItem]
