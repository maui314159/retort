from pydantic import BaseModel, Field, field_validator
from typing import Optional

class BookCreate(BaseModel):
    """Model for creating a new book."""
    title: str = Field(..., min_length=1, description="Book title")
    author: str = Field(..., min_length=1, description="Book author")
    year: Optional[int] = Field(None, ge=1000, le=2100, description="Publication year")
    isbn: Optional[str] = Field(None, description="ISBN")

    @field_validator('title', 'author')
    @classmethod
    def validate_non_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('must not be empty')
        return v.strip()

class BookUpdate(BaseModel):
    """Model for updating an existing book."""
    title: Optional[str] = Field(None, min_length=1, description="Book title")
    author: Optional[str] = Field(None, min_length=1, description="Book author")
    year: Optional[int] = Field(None, ge=1000, le=2100, description="Publication year")
    isbn: Optional[str] = Field(None, description="ISBN")

    @field_validator('title', 'author')
    @classmethod
    def validate_non_empty_update(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('must not be empty')
        if v is not None:
            return v.strip()
        return v

class BookResponse(BaseModel):
    """Model for book response."""
    id: int
    title: str
    author: str
    year: Optional[int]
    isbn: Optional[str]
    created_at: str
