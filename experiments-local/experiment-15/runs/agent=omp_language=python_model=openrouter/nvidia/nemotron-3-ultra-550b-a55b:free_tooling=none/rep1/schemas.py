from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class BookBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    author: str = Field(..., min_length=1, max_length=255)
    year: Optional[int] = Field(None, ge=1000, le=2100)
    isbn: Optional[str] = Field(None, pattern=r"^\d{10}(\d{3})?$")


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    author: Optional[str] = Field(None, min_length=1, max_length=255)
    year: Optional[int] = Field(None, ge=1000, le=2100)
    isbn: Optional[str] = Field(None, pattern=r"^\d{10}(\d{3})?$")


class Book(BookBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
