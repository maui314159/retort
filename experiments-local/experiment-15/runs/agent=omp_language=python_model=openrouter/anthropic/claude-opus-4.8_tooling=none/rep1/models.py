"""Request/response schemas for the book API."""

from pydantic import BaseModel, Field, field_validator


def _require_nonblank(v: str) -> str:
    stripped = v.strip()
    if not stripped:
        raise ValueError("must not be blank")
    return stripped


class BookCreate(BaseModel):
    title: str = Field(..., min_length=1, description="Book title (required)")
    author: str = Field(..., min_length=1, description="Author name (required)")
    year: int | None = None
    isbn: str | None = None

    @field_validator("title", "author")
    @classmethod
    def _strip(cls, v: str) -> str:
        return _require_nonblank(v)


class BookUpdate(BaseModel):
    """Full replacement of a book's mutable fields (PUT semantics)."""

    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    year: int | None = None
    isbn: str | None = None

    @field_validator("title", "author")
    @classmethod
    def _strip(cls, v: str) -> str:
        return _require_nonblank(v)


class Book(BaseModel):
    id: int
    title: str
    author: str
    year: int | None = None
    isbn: str | None = None
