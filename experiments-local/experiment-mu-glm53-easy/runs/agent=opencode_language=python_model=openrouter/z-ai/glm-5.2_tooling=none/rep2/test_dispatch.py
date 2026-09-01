"""Unit tests for BookAPI dispatch + validation logic (no sockets)."""
import pytest

from app import BookAPI, APIError
from bookdb import BookDB


@pytest.fixture
def api():
    return BookAPI(db=BookDB(":memory:"))


def _create(api, title="Dune", author="Frank Herbert", year=1965, isbn=None):
    body = {"title": title, "author": author, "year": year}
    if isbn is not None:
        body["isbn"] = isbn
    return api.dispatch("POST", "/books", {}, body)


# --- health -----------------------------------------------------------------

def test_health(api):
    status, body = api.dispatch("GET", "/health", {}, None)
    assert status == 200
    assert body == {"status": "ok"}


# --- create + read ----------------------------------------------------------

def test_create_and_get(api):
    status, created = _create(api)
    assert status == 201
    assert created["title"] == "Dune"
    assert created["author"] == "Frank Herbert"
    assert created["year"] == 1965
    assert isinstance(created["id"], int)

    status, fetched = api.dispatch("GET", f"/books/{created['id']}", {}, None)
    assert status == 200
    assert fetched == created


def test_create_requires_title(api):
    with pytest.raises(APIError) as exc:
        api.dispatch("POST", "/books", {}, {"author": "X"})
    assert exc.value.status == 400


def test_create_requires_author(api):
    with pytest.raises(APIError) as exc:
        api.dispatch("POST", "/books", {}, {"title": "X"})
    assert exc.value.status == 400


def test_create_rejects_empty_strings(api):
    with pytest.raises(APIError):
        api.dispatch("POST", "/books", {}, {"title": "   ", "author": "X"})


def test_create_rejects_bad_year(api):
    with pytest.raises(APIError):
        api.dispatch("POST", "/books", {}, {"title": "T", "author": "A", "year": "1965"})
    with pytest.raises(APIError):
        api.dispatch("POST", "/books", {}, {"title": "T", "author": "A", "year": -1})


def test_create_rejects_non_json_body(api):
    with pytest.raises(APIError):
        api.dispatch("POST", "/books", {}, None)


# --- list + filter ----------------------------------------------------------

def test_list_and_author_filter(api):
    _create(api, title="Dune", author="Frank Herbert")
    _create(api, title="1984", author="George Orwell")

    status, books = api.dispatch("GET", "/books", {}, None)
    assert status == 200
    assert len(books) == 2

    status, filtered = api.dispatch("GET", "/books", {"author": ["George Orwell"]}, None)
    assert status == 200
    assert len(filtered) == 1
    assert filtered[0]["title"] == "1984"

    status, none = api.dispatch("GET", "/books", {"author": ["Nobody"]}, None)
    assert status == 200
    assert none == []


# --- update -----------------------------------------------------------------

def test_update_partial(api):
    _, created = _create(api)
    status, updated = api.dispatch(
        "PUT", f"/books/{created['id']}", {}, {"year": 1970}
    )
    assert status == 200
    assert updated["year"] == 1970
    assert updated["title"] == "Dune"


def test_update_missing_book_404(api):
    with pytest.raises(APIError) as exc:
        api.dispatch("PUT", "/books/9999", {}, {"year": 1970})
    assert exc.value.status == 404


def test_update_validates_types(api):
    _, created = _create(api)
    with pytest.raises(APIError):
        api.dispatch("PUT", f"/books/{created['id']}", {}, {"title": 123})


# --- delete -----------------------------------------------------------------

def test_delete(api):
    _, created = _create(api)
    status, body = api.dispatch("DELETE", f"/books/{created['id']}", {}, None)
    assert status == 204
    assert body is None

    with pytest.raises(APIError) as exc:
        api.dispatch("GET", f"/books/{created['id']}", {}, None)
    assert exc.value.status == 404


def test_delete_missing_404(api):
    with pytest.raises(APIError) as exc:
        api.dispatch("DELETE", "/books/9999", {}, None)
    assert exc.value.status == 404


def test_unknown_route_404(api):
    with pytest.raises(APIError) as exc:
        api.dispatch("GET", "/nope", {}, None)
    assert exc.value.status == 404
