from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional


class BookBase(BaseModel):
    """Base model for book data."""
    model_config = ConfigDict(from_attributes=True)

    title: str = Field(..., min_length=1, description="Book title")
    author: str = Field(..., min_length=1, description="Book author")
    year: Optional[int] = Field(None, ge=1000, le=2100, description="Publication year")
    isbn: Optional[str] = Field(None, description="ISBN number")

    @field_validator('title', 'author')
    @classmethod
    def validate_non_empty(cls, v: str, info):
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} cannot be empty")
        return v.strip()


class BookCreate(BookBase):
    """Model for creating a new book."""
    pass


class BookUpdate(BaseModel):
    """Model for updating a book (all fields optional)."""
    model_config = ConfigDict(from_attributes=True)

    title: Optional[str] = Field(None, min_length=1)
    author: Optional[str] = Field(None, min_length=1)
    year: Optional[int] = Field(None, ge=1000, le=2100)
    isbn: Optional[str] = None

    @field_validator('title', 'author')
    @classmethod
    def validate_non_empty(cls, v: Optional[str], info):
        if v is not None and not v.strip():
            raise ValueError(f"{info.field_name} cannot be empty if provided")
        return v.strip() if v else v


class BookResponse(BookBase):
    """Model for book response with ID."""
    id: int
