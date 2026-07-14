from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class BookBase(BaseModel):
    title: str = Field(..., min_length=1, description="Book title")
    author: str = Field(..., min_length=1, description="Book author")
    year: Optional[int] = Field(None, ge=0, le=9999, description="Publication year")
    isbn: Optional[str] = Field(None, description="ISBN identifier")


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, description="Book title")
    author: Optional[str] = Field(None, min_length=1, description="Book author")
    year: Optional[int] = Field(None, ge=0, le=9999, description="Publication year")
    isbn: Optional[str] = Field(None, description="ISBN identifier")

    @field_validator("title", "author")
    @classmethod
    def not_empty(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value.strip() == "":
            raise ValueError("field cannot be empty")
        return value


class Book(BookBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
