from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "books.db"


class Base(DeclarativeBase):
    pass


def _resolve_url(database_url: str | None = None) -> str:
    if database_url:
        return database_url
    return f"sqlite:///{_DEFAULT_DB_PATH}"


def make_engine(database_url: str | None = None):
    url = _resolve_url(database_url)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, future=True)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    # Import here to avoid circular import at module load time.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
