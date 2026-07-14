"""Pydantic models for the books API.

These define the request/response shapes and enforce validation:
`title` and `author` are required (non-empty strings), `year` is an
optional integer, `isbn` is an optional string.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BookBase(BaseModel):
    title: str = Field(..., description="Title of the book")
    author: str = Field(..., description="Author of the book")
    year: int | None = Field(default=None, description="Publication year")
    isbn: str | None = Field(default=None, description="ISBN identifier")

    @field_validator("title", "author")
    @classmethod
    def _must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be blank")
        return v.strip()


class BookCreate(BookBase):
    """Body for POST /books."""
    pass


class BookUpdate(BookBase):
    """Body for PUT /books/{id}.

    Same required fields as create: a full replacement of the book.
    """
    pass


class Book(BookBase):
    """Book as returned in responses, with its id."""
    id: int

    model_config = ConfigDict(from_attributes=True)
