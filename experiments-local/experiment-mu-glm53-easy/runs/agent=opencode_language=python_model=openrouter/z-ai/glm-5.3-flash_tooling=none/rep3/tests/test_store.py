"""Unit tests for the SQLite store and the payload validation logic."""

import pytest

from app import BookStore, validate_book_payload


def test_validate_requires_title_and_author():
    fields, errors = validate_book_payload({})
    assert fields == {}
    assert any("title" in message for message in errors)
    assert any("author" in message for message in errors)


def test_validate_strips_and_normalizes_valid_payload():
    fields, errors = validate_book_payload(
        {"title": "  Dune ", "author": " Frank Herbert ", "year": "1965", "isbn": " 978-0441172719 "}
    )
    assert errors == []
    assert fields == {
        "title": "Dune",
        "author": "Frank Herbert",
        "year": 1965,
        "isbn": "978-0441172719",
    }


def test_validate_partial_mode_ignores_missing_fields():
    fields, errors = validate_book_payload({"year": 2000}, partial=True)
    assert errors == []
    assert fields == {"year": 2000}


def test_validate_non_object_payload():
    fields, errors = validate_book_payload(["nope"])
    assert fields == {}
    assert errors == ["request body must be a JSON object"]


def test_validate_coerces_numeric_isbn_to_string():
    fields, errors = validate_book_payload({"title": "t", "author": "a", "isbn": 12345})
    assert errors == []
    assert fields["isbn"] == "12345"


@pytest.mark.parametrize("bad_year", [True, 3.5, "abc", [], {}])
def test_validate_rejects_invalid_year_values(bad_year):
    fields, errors = validate_book_payload({"title": "t", "author": "a", "year": bad_year})
    assert any("year" in message for message in errors)


def test_store_create_and_get(tmp_path):
    store = BookStore(str(tmp_path / "books.db"))
    book = store.create(title="Dune", author="Frank Herbert", year=1965, isbn="978-0441172719")
    assert book["id"] == 1
    assert store.get(book["id"]) == book
    assert store.get(999) is None


def test_store_list_and_author_filter(tmp_path):
    store = BookStore(str(tmp_path / "books.db"))
    store.create(title="Dune", author="Frank Herbert")
    store.create(title="The Hobbit", author="J. R. R. Tolkien")
    assert len(store.list_books()) == 2
    assert [book["title"] for book in store.list_books(author="herbert")] == ["Dune"]
    assert store.list_books(author="zzz") == []


def test_store_update(tmp_path):
    store = BookStore(str(tmp_path / "books.db"))
    book = store.create(title="Dune", author="Frank Herbert", year=1965)
    updated = store.update(book["id"], {"year": 1976, "isbn": None})
    assert updated["year"] == 1976
    assert updated["isbn"] is None
    assert updated["title"] == "Dune"
    assert store.update(999, {"year": 2000}) is None


def test_store_delete(tmp_path):
    store = BookStore(str(tmp_path / "books.db"))
    book = store.create(title="Dune", author="Frank Herbert")
    assert store.delete(book["id"]) is True
    assert store.delete(book["id"]) is False
    assert store.get(book["id"]) is None


def test_store_persists_across_instances(tmp_path):
    path = str(tmp_path / "books.db")
    BookStore(path).create(title="Dune", author="Frank Herbert")
    second = BookStore(path)
    books = second.list_books()
    assert len(books) == 1
    assert books[0]["title"] == "Dune"
