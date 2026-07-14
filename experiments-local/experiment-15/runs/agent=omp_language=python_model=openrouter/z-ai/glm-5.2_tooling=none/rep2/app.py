"""Books REST API.

FastAPI service backed by SQLite (see `db.py`). Exposes CRUD endpoints
for a book collection plus a `/health` probe.

The DB is initialized at import time so `uvicorn app:app` "just works".
Tests use `init_db(fresh=True)` to start clean.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Response

import db
from models import Book, BookCreate, BookUpdate


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="Books API", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/books", response_model=Book, status_code=201)
def create_book(payload: BookCreate) -> dict:
    return db.insert_book(payload.model_dump())


@app.get("/books", response_model=list[Book])
def list_books(author: str | None = Query(default=None)) -> list[dict]:
    return db.list_books(author=author)


@app.get("/books/{bid}", response_model=Book)
def get_book(bid: int) -> dict:
    book = db.get_book(bid)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@app.put("/books/{bid}", response_model=Book)
def update_book(bid: int, payload: BookUpdate) -> dict:
    updated = db.update_book(bid, payload.model_dump())
    if updated is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return updated


@app.delete("/books/{bid}")
def delete_book(bid: int) -> Response:
    if not db.delete_book(bid):
        raise HTTPException(status_code=404, detail="Book not found")
    return Response(status_code=204)
