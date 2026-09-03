import os
import tempfile

import pytest

import app as app_module


@pytest.fixture
def client(tmp_path):
    db_path = str(tmp_path / "test_books.db")
    os.environ["BOOKS_DB_PATH"] = db_path
    app_module.DB_PATH = db_path
    app_module.init_db(db_path)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c
    os.environ.pop("BOOKS_DB_PATH", None)


def valid_book(**overrides):
    payload = {"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}
    payload.update(overrides)
    return payload
