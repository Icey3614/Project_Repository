from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.movie import Movie
from app.models.session import MovieSession
from app.models.session_seat import SessionSeat
from app.models.user import User
from app.models.venue import Venue
from app.models.venue_seat import VenueSeat


def seed() -> None:
    with SessionLocal() as db:
        # 用户
        if db.scalar(select(User).where(User.username == "admin")) is None:
            db.add(
                User(
                    username="admin",
                    password_hash=hash_password("Admin@123456"),
                    nickname="管理员",
                    role="ADMIN",
                )
            )
        if db.scalar(select(User).where(User.username == "demo")) is None:
            db.add(
                User(
                    username="demo",
                    password_hash=hash_password("Demo@123456"),
                    nickname="演示用户",
                    role="USER",
                )
            )

        # 电影
        movies = [
            ("太空漫游", 148, "经典科幻重映：人类探索星际奥秘的史诗旅程。"),
            ("深海奇缘", 105, "动画冒险：女孩与海豚的奇幻之旅。"),
            ("城市之光", 118, "现实题材：都市青年在理想与现实之间的抉择。"),
        ]
        for title, duration, description in movies:
            if db.scalar(select(Movie).where(Movie.title == title)) is None:
                db.add(
                    Movie(
                        title=title,
                        duration_min=duration,
                        description=description,
                        poster_url=None,
                    )
                )

        # 场馆（含座位模板，四角禁用模拟实际布局）
        venues = [("1号厅", 8, 12), ("2号厅", 10, 14)]
        for name, rows, cols in venues:
            if db.scalar(select(Venue).where(Venue.name == name)) is None:
                venue = Venue(
                    name=name,
                    rows=rows,
                    cols=cols,
                    capacity=rows * cols,
                    screen_pos={"position": "front"},
                    exits=[
                        {"label": "入口A", "side": "left"},
                        {"label": "入口B", "side": "right"},
                    ],
                    status="ACTIVE",
                )
                db.add(venue)
                db.flush()
                for r in range(1, rows + 1):
                    for c in range(1, cols + 1):
                        is_corner = (r == 1 or r == rows) and (c == 1 or c == cols)
                        db.add(
                            VenueSeat(
                                venue_id=venue.id,
                                row_no=r,
                                col_no=c,
                                seat_no=f"{chr(64 + r)}{c}",
                                enabled=not is_corner,
                            )
                        )

        # 场次（未来 3 天，每天 10:00 / 19:00 两场，天然满足 30 分钟清扫缓冲）
        today = date.today()
        slots = [(10, 0), (19, 0)]
        movies = db.scalars(select(Movie).order_by(Movie.id)).all()
        venues = db.scalars(select(Venue).order_by(Venue.id)).all()
        for day_offset in range(1, 4):
            for venue in venues:
                for idx, (hh, mm) in enumerate(slots):
                    movie = movies[idx % len(movies)]
                    start = datetime.combine(today + timedelta(days=day_offset), time(hh, mm))
                    exists = db.scalar(
                        select(func.count())
                        .select_from(MovieSession)
                        .where(MovieSession.venue_id == venue.id, MovieSession.start_at == start)
                    )
                    if exists:
                        continue
                    end = start + timedelta(minutes=movie.duration_min)
                    session = MovieSession(
                        movie_id=movie.id,
                        venue_id=venue.id,
                        start_at=start,
                        end_at=end,
                        sale_open_at=start - timedelta(days=3),
                        sale_close_at=start - timedelta(minutes=30),
                        base_price=45,
                    )
                    db.add(session)
                    db.flush()
                    template_seats = db.scalars(
                        select(VenueSeat).where(VenueSeat.venue_id == venue.id)
                    ).all()
                    for ts in template_seats:
                        db.add(
                            SessionSeat(
                                session_id=session.id,
                                row_no=ts.row_no,
                                col_no=ts.col_no,
                                seat_no=ts.seat_no,
                                price=45,
                                status="AVAILABLE" if ts.enabled else "DISABLED",
                            )
                        )

        db.commit()

    print("种子数据完成：admin/Admin@123456、demo/Demo@123456、3 部电影、2 个场馆、12 个场次")


if __name__ == "__main__":
    seed()
