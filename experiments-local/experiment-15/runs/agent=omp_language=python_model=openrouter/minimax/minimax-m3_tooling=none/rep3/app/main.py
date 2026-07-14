from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db, init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Book Collection API", version="1.0.0", lifespan=lifespan)


@app.get("/health", response_model=schemas.HealthOut, tags=["health"])
def health() -> schemas.HealthOut:
    return schemas.HealthOut(status="ok")


@app.post(
    "/books",
    response_model=schemas.BookOut,
    status_code=status.HTTP_201_CREATED,
    tags=["books"],
)
def create_book(payload: schemas.BookCreate, db: Session = Depends(get_db)) -> models.Book:
    book = models.Book(**payload.model_dump())
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


@app.get("/books", response_model=list[schemas.BookOut], tags=["books"])
def list_books(
    author: str | None = Query(default=None, description="Case-insensitive author filter"),
    db: Session = Depends(get_db),
) -> list[models.Book]:
    stmt = select(models.Book)
    if author is not None:
        stmt = stmt.where(models.Book.author.ilike(f"%{author}%"))
    stmt = stmt.order_by(models.Book.id)
    return list(db.scalars(stmt).all())


@app.get("/books/{book_id}", response_model=schemas.BookOut, tags=["books"])
def get_book(book_id: int, db: Session = Depends(get_db)) -> models.Book:
    book = db.get(models.Book, book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return book


@app.put("/books/{book_id}", response_model=schemas.BookOut, tags=["books"])
def update_book(
    book_id: int,
    payload: schemas.BookUpdate,
    db: Session = Depends(get_db),
) -> models.Book:
    book = db.get(models.Book, book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    for field, value in payload.model_dump().items():
        setattr(book, field, value)
    db.commit()
    db.refresh(book)
    return book


@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["books"])
def delete_book(book_id: int, db: Session = Depends(get_db)) -> Response:
    book = db.get(models.Book, book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    db.delete(book)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
