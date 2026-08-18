from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.core.exceptions import BizError, NotFoundError
from app.db.session import get_db
from app.models.movie import Movie
from app.models.session import MovieSession
from app.models.user import User
from app.schemas.common import Envelope, Page
from app.schemas.movie import MovieCreate, MovieOut, MovieUpdate

router = APIRouter()


@router.get("", response_model=Envelope[Page[MovieOut]])
def list_movies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
):
    base = select(Movie)
    if keyword:
        base = base.where(Movie.title.contains(keyword))
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    items = db.scalars(
        base.order_by(Movie.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Envelope(
        data=Page(
            items=[MovieOut.model_validate(m) for m in items],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/{movie_id}", response_model=Envelope[MovieOut])
def get_movie(movie_id: int, db: Session = Depends(get_db)):
    movie = db.get(Movie, movie_id)
    if movie is None:
        raise NotFoundError("电影不存在")
    return Envelope(data=MovieOut.model_validate(movie))


@router.post("", response_model=Envelope[MovieOut], status_code=201)
def create_movie(
    payload: MovieCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    movie = Movie(**payload.model_dump())
    db.add(movie)
    db.commit()
    db.refresh(movie)
    return Envelope(data=MovieOut.model_validate(movie))


@router.put("/{movie_id}", response_model=Envelope[MovieOut])
def update_movie(
    movie_id: int,
    payload: MovieUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    movie = db.get(Movie, movie_id)
    if movie is None:
        raise NotFoundError("电影不存在")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(movie, key, value)
    db.commit()
    db.refresh(movie)
    return Envelope(data=MovieOut.model_validate(movie))


@router.delete("/{movie_id}", response_model=Envelope[None])
def delete_movie(
    movie_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    movie = db.get(Movie, movie_id)
    if movie is None:
        raise NotFoundError("电影不存在")
    if db.scalar(
        select(func.count()).select_from(MovieSession).where(MovieSession.movie_id == movie_id)
    ):
        raise BizError("该电影已有场次，禁止删除")
    db.delete(movie)
    db.commit()
    return Envelope(data=None)
