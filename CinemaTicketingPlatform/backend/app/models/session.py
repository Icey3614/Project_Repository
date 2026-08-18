from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MovieSession(Base):
    __tablename__ = "sessions"
    __table_args__ = (Index("ix_sessions_venue_start", "venue_id", "start_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    venue_id: Mapped[int] = mapped_column(
        ForeignKey("venues.id", ondelete="CASCADE"), index=True, nullable=False
    )
    start_at: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    sale_open_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    sale_close_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    base_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    movie: Mapped["Movie"] = relationship()
    venue: Mapped["Venue"] = relationship()
