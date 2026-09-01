"""Integration tests for the books REST API (HTTP-level, via Flask test client)."""

import pytest


@pytest.fixture()
def created_book(client):
    res = client.post(
        "/books",
        json={"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"},
    )
    assert res.status_code == 201
    return res.get_json()


class TestHealth:
    def test_health_returns_ok(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.get_json() == {"status": "ok"}


class TestCreateBook:
    def test_create_returns_201_and_book(self, client):
        res = client.post(
            "/books",
            json={"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"},
        )
        assert res.status_code == 201
        assert res.get_json() == {
            "id": 1,
            "title": "Dune",
            "author": "Frank Herbert",
            "year": 1965,
            "isbn": "978-0441172719",
        }

    def test_create_with_optional_fields_omitted(self, client):
        res = client.post("/books", json={"title": "Ficciones", "author": "Jorge Luis Borges"})
        assert res.status_code == 201
        book = res.get_json()
        assert book["year"] is None
        assert book["isbn"] is None

    def test_create_missing_author_is_rejected(self, client):
        res = client.post("/books", json={"title": "No Author"})
        assert res.status_code == 400
        body = res.get_json()
        assert "error" in body
        assert any("author" in detail for detail in body["details"])

    def test_create_missing_title_is_rejected(self, client):
        res = client.post("/books", json={"author": "Nobody"})
        assert res.status_code == 400

    def test_create_blank_title_is_rejected(self, client):
        res = client.post("/books", json={"title": "   ", "author": "Someone"})
        assert res.status_code == 400

    def test_create_non_string_author_is_rejected(self, client):
        res = client.post("/books", json={"title": "T", "author": 42})
        assert res.status_code == 400

    def test_create_non_integer_year_is_rejected(self, client):
        res = client.post("/books", json={"title": "T", "author": "A", "year": "not-a-year"})
        assert res.status_code == 400

    def test_create_non_json_body_is_rejected(self, client):
        res = client.post("/books", data="not json", content_type="text/plain")
        assert res.status_code == 400

    def test_create_array_body_is_rejected(self, client):
        res = client.post("/books", json=[1, 2, 3])
        assert res.status_code == 400


class TestListBooks:
    def test_list_returns_all_books(self, client):
        client.post("/books", json={"title": "Dune", "author": "Frank Herbert"})
        client.post("/books", json={"title": "Hamlet", "author": "William Shakespeare"})
        res = client.get("/books")
        assert res.status_code == 200
        books = res.get_json()
        assert len(books) == 2
        assert {b["title"] for b in books} == {"Dune", "Hamlet"}

    def test_list_empty_collection(self, client):
        res = client.get("/books")
        assert res.status_code == 200
        assert res.get_json() == []

    def test_list_filters_by_author_substring_case_insensitive(self, client):
        client.post("/books", json={"title": "Dune", "author": "Frank Herbert"})
        client.post("/books", json={"title": "Hamlet", "author": "William Shakespeare"})
        res = client.get("/books", query_string={"author": "herbert"})
        assert res.status_code == 200
        books = res.get_json()
        assert len(books) == 1
        assert books[0]["title"] == "Dune"

    def test_list_filter_with_no_match_returns_empty(self, client):
        client.post("/books", json={"title": "Dune", "author": "Frank Herbert"})
        res = client.get("/books", query_string={"author": "Rowling"})
        assert res.status_code == 200
        assert res.get_json() == []


class TestGetBook:
    def test_get_existing_book(self, client, created_book):
        res = client.get(f"/books/{created_book['id']}")
        assert res.status_code == 200
        assert res.get_json() == created_book

    def test_get_missing_book_returns_404(self, client):
        res = client.get("/books/9999")
        assert res.status_code == 404
        assert "error" in res.get_json()

    def test_get_non_numeric_id_returns_404(self, client):
        res = client.get("/books/abc")
        assert res.status_code == 404


class TestUpdateBook:
    def test_update_replaces_fields(self, client, created_book):
        res = client.put(
            f"/books/{created_book['id']}",
            json={"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969},
        )
        assert res.status_code == 200
        assert res.get_json() == {
            "id": created_book["id"],
            "title": "Dune Messiah",
            "author": "Frank Herbert",
            "year": 1969,
            "isbn": None,
        }

    def test_update_accepts_numeric_string_year(self, client, created_book):
        res = client.put(
            f"/books/{created_book['id']}",
            json={"title": "T", "author": "A", "year": "1999", "isbn": "1234567890"},
        )
        assert res.status_code == 200
        assert res.get_json()["year"] == 1999

    def test_update_missing_book_returns_404(self, client):
        res = client.put("/books/9999", json={"title": "T", "author": "A"})
        assert res.status_code == 404

    def test_update_without_required_fields_returns_400(self, client, created_book):
        res = client.put(f"/books/{created_book['id']}", json={"title": "Only Title"})
        assert res.status_code == 400

    def test_update_invalid_body_returns_400(self, client, created_book):
        res = client.put(f"/books/{created_book['id']}", data="nope", content_type="text/plain")
        assert res.status_code == 400


class TestDeleteBook:
    def test_delete_returns_204_then_book_is_gone(self, client, created_book):
        res = client.delete(f"/books/{created_book['id']}")
        assert res.status_code == 204
        assert res.data == b""
        assert client.get(f"/books/{created_book['id']}").status_code == 404

    def test_delete_missing_book_returns_404(self, client):
        res = client.delete("/books/9999")
        assert res.status_code == 404

    def test_delete_twice_returns_404_second_time(self, client, created_book):
        assert client.delete(f"/books/{created_book['id']}").status_code == 204
        assert client.delete(f"/books/{created_book['id']}").status_code == 404


class TestMiscRoutes:
    def test_unknown_route_returns_json_404(self, client):
        res = client.get("/nope")
        assert res.status_code == 404
        assert "error" in res.get_json()

    def test_wrong_method_returns_json_405(self, client):
        res = client.patch("/books")
        assert res.status_code == 405
        assert "error" in res.get_json()
