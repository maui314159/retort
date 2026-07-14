from pydantic import BaseModel, field_validator


class BookCreate(BaseModel):
    title: str
    author: str
    year: int | None = None
    isbn: str | None = None

    @field_validator("title", "author")
    @classmethod
    def must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v.strip()


class BookUpdate(BaseModel):
    title: str | None = None
    author: str | None = None
    year: int | None = None
    isbn: str | None = None

    @field_validator("title", "author")
    @classmethod
    def must_not_be_blank(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("must not be blank")
        return v.strip() if v is not None else v


class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    year: int | None
    isbn: str | None

    model_config = {"from_attributes": True}
