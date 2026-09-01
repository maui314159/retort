import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path):
    """Flask test client backed by a fresh SQLite database per test."""
    app = create_app(database_path=str(tmp_path / "test-books.db"))
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client
