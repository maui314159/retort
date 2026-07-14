from typing import Optional

from pydantic import BaseModel, field_validator


class BookCreate(BaseModel):
    title: str
    author: str
    year: Optional[int] = None
    isbn: Optional[str] = None

    @field_validator("title", "author")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty")
        return v.strip()

    @field_validator("year")
    @classmethod
    def valid_year(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("year must be non-negative")
        return v


class BookUpdate(BaseModel):
    title: str
    author: str
    year: Optional[int] = None
    isbn: Optional[str] = None

    @field_validator("title", "author")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty")
        return v.strip()

    @field_validator("year")
    @classmethod
    def valid_year(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("year must be non-negative")
        return v
