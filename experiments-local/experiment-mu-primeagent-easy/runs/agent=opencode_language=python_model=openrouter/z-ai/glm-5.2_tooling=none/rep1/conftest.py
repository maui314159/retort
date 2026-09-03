"""Pytest configuration: use an isolated temp database for every test session."""
import os
import tempfile

_DB_FD, _DB_PATH = tempfile.mkstemp(suffix=".db")
os.environ["BOOKS_DB_PATH"] = _DB_PATH

import pytest
from app import app, init_db


@pytest.fixture()
def client():
    """Provide a fresh Flask test client backed by an empty DB."""
    init_db()
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def _clean_db():
    """Truncate the books table before each test for isolation."""
    import sqlite3
    from app import get_db_path

    conn = sqlite3.connect(get_db_path())
    conn.execute("DELETE FROM books")
    conn.commit()
    conn.close()
    yield
