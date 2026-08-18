from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MovieCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    poster_url: str | None = Field(default=None, max_length=500)
    duration_min: int = Field(ge=1, le=600)
    description: str | None = None


class MovieUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    poster_url: str | None = Field(default=None, max_length=500)
    duration_min: int | None = Field(default=None, ge=1, le=600)
    description: str | None = None


class MovieOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    poster_url: str | None
    duration_min: int
    description: str | None
    created_at: datetime
