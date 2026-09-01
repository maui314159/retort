"""Shared pytest fixtures for the book API tests."""

import pytest

from app import create_app


@pytest.fixture()
def client():
    """A Flask test client backed by a fresh in-memory database."""
    app = create_app({"TESTING": True, "DATABASE": ":memory:"})
    with app.test_client() as test_client:
        yield test_client
    app.extensions["books_db"].close()
