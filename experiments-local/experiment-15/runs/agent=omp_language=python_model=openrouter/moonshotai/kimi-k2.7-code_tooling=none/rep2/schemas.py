from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class BookBase(BaseModel):
    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    year: Optional[int] = None
    isbn: Optional[str] = None


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1)
    author: Optional[str] = Field(None, min_length=1)
    year: Optional[int] = None
    isbn: Optional[str] = None


class BookResponse(BookBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
