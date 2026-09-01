"""Unit tests for the request payload validation logic."""

import pytest

from app import ValidationError, validate_book_payload


def test_valid_payload_returns_cleaned_fields():
    fields = validate_book_payload({"title": "  Dune  ", "author": " Frank Herbert "})
    assert fields == {"title": "Dune", "author": "Frank Herbert"}


def test_valid_payload_includes_optional_fields():
    fields = validate_book_payload(
        {"title": "T", "author": "A", "year": 2001, "isbn": " 123-X "}
    )
    assert fields == {"title": "T", "author": "A", "year": 2001, "isbn": "123-X"}


def test_missing_author_raises_with_detail():
    with pytest.raises(ValidationError) as excinfo:
        validate_book_payload({"title": "T"})
    assert any("author" in detail for detail in excinfo.value.details)


def test_missing_title_raises_with_detail():
    with pytest.raises(ValidationError) as excinfo:
        validate_book_payload({"author": "A"})
    assert any("title" in detail for detail in excinfo.value.details)


def test_null_required_field_raises():
    with pytest.raises(ValidationError):
        validate_book_payload({"title": None, "author": "A"})


def test_non_dict_payload_raises():
    with pytest.raises(ValidationError):
        validate_book_payload(["not", "a", "dict"])


def test_numeric_string_year_is_coerced_to_int():
    fields = validate_book_payload({"title": "T", "author": "A", "year": " 1984 "})
    assert fields["year"] == 1984


def test_invalid_year_raises():
    with pytest.raises(ValidationError):
        validate_book_payload({"title": "T", "author": "A", "year": "MCMLXXXIV"})


def test_boolean_year_raises():
    with pytest.raises(ValidationError):
        validate_book_payload({"title": "T", "author": "A", "year": True})


def test_non_string_isbn_raises():
    with pytest.raises(ValidationError):
        validate_book_payload({"title": "T", "author": "A", "isbn": 123})


def test_unknown_fields_are_ignored():
    fields = validate_book_payload({"title": "T", "author": "A", "publisher": "Ace"})
    assert fields == {"title": "T", "author": "A"}


def test_multiple_problems_are_collected():
    with pytest.raises(ValidationError) as excinfo:
        validate_book_payload({"year": "abc"})
    # Missing title, missing author, and a non-integer year are all reported.
    assert len(excinfo.value.details) == 3
    assert any("year" in detail for detail in excinfo.value.details)
