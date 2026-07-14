from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional

class BookBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    author: str = Field(..., min_length=1, max_length=255)
    year: Optional[int] = Field(None, ge=1000, le=2100)
    isbn: Optional[str] = Field(None, pattern=r"^[0-9\-]+$", max_length=20)

    @field_validator("title", "author")
    def not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("must not be empty")
        return v.strip()

class BookCreate(BookBase):
    pass

class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    author: Optional[str] = Field(None, min_length=1, max_length=255)
    year: Optional[int] = Field(None, ge=1000, le=2100)
    isbn: Optional[str] = Field(None, pattern=r"^[0-9\-]+$", max_length=20)

class BookResponse(BookBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True