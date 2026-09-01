"""Integration tests for the book collection REST API.

Each test runs against its own throwaway SQLite database, so tests are fully
isolated from each other and from any developer database.
"""

import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app(db_path=str(tmp_path / "books.db"))
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def make_payload(**overrides):
    payload = {
        "title": "Dune",
        "author": "Frank Herbert",
        "year": 1965,
        "isbn": "978-0441172719",
    }
    payload.update(overrides)
    return payload


def error_details(response):
    return " ".join(response.get_json().get("details", []))


class TestHealth:
    def test_returns_ok_status(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.get_json() == {"status": "ok"}


class TestCreateBook:
    def test_creates_book_and_returns_201(self, client):
        response = client.post("/books", json=make_payload())
        assert response.status_code == 201
        data = response.get_json()
        assert data["id"] == 1
        assert data["title"] == "Dune"
        assert data["author"] == "Frank Herbert"
        assert data["year"] == 1965
        assert data["isbn"] == "978-0441172719"
        assert response.headers["Location"] == "/books/1"

    def test_allows_omitting_optional_fields(self, client):
        response = client.post(
            "/books", json={"title": "The Left Hand of Darkness", "author": "Ursula K. Le Guin"}
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["year"] is None
        assert data["isbn"] is None

    def test_trims_surrounding_whitespace(self, client):
        response = client.post("/books", json=make_payload(title="  Dune  "))
        assert response.status_code == 201
        assert response.get_json()["title"] == "Dune"

    def test_rejects_missing_title(self, client):
        payload = make_payload()
        del payload["title"]
        response = client.post("/books", json=payload)
        assert response.status_code == 400
        assert "title" in error_details(response)

    def test_rejects_missing_author(self, client):
        payload = make_payload()
        del payload["author"]
        response = client.post("/books", json=payload)
        assert response.status_code == 400
        assert "author" in error_details(response)

    def test_rejects_blank_title(self, client):
        response = client.post("/books", json=make_payload(title="   "))
        assert response.status_code == 400

    def test_rejects_non_string_author(self, client):
        response = client.post("/books", json=make_payload(author=42))
        assert response.status_code == 400

    def test_rejects_non_integer_year(self, client):
        response = client.post("/books", json=make_payload(year="nineteen eighty-four"))
        assert response.status_code == 400
        assert "year" in error_details(response)

    def test_rejects_year_out_of_range(self, client):
        response = client.post("/books", json=make_payload(year=12345))
        assert response.status_code == 400

    def test_coerces_numeric_string_year(self, client):
        response = client.post("/books", json=make_payload(year="1965"))
        assert response.status_code == 201
        assert response.get_json()["year"] == 1965

    def test_rejects_malformed_json_body(self, client):
        response = client.post("/books", data="{not json", content_type="application/json")
        assert response.status_code == 400
        assert "error" in response.get_json()

    def test_rejects_non_object_json_body(self, client):
        response = client.post("/books", json=["not", "an", "object"])
        assert response.status_code == 400


class TestListBooks:
    def test_empty_collection_returns_empty_list(self, client):
        response = client.get("/books")
        assert response.status_code == 200
        assert response.get_json() == []

    def test_lists_all_books_in_creation_order(self, client):
        client.post("/books", json=make_payload())
        client.post(
            "/books",
            json=make_payload(title="Neuromancer", author="William Gibson", year=1984),
        )
        response = client.get("/books")
        assert response.status_code == 200
        data = response.get_json()
        assert [book["id"] for book in data] == [1, 2]
        assert data[1]["title"] == "Neuromancer"

    def test_filters_by_author(self, client):
        client.post("/books", json=make_payload())
        client.post(
            "/books",
            json=make_payload(title="Neuromancer", author="William Gibson", year=1984),
        )
        client.post(
            "/books",
            json=make_payload(title="Count Zero", author="William Gibson", year=1986),
        )
        response = client.get("/books", query_string={"author": "William Gibson"})
        assert response.status_code == 200
        data = response.get_json()
        assert {book["title"] for book in data} == {"Neuromancer", "Count Zero"}

    def test_author_filter_with_no_matches_returns_empty_list(self, client):
        client.post("/books", json=make_payload())
        response = client.get("/books", query_string={"author": "Nobody"})
        assert response.status_code == 200
        assert response.get_json() == []


class TestGetBook:
    def test_returns_book_by_id(self, client):
        created = client.post("/books", json=make_payload()).get_json()
        response = client.get(f"/books/{created['id']}")
        assert response.status_code == 200
        assert response.get_json() == created

    def test_returns_404_for_unknown_id(self, client):
        response = client.get("/books/999")
        assert response.status_code == 404
        assert "error" in response.get_json()

    def test_returns_json_404_for_non_numeric_id(self, client):
        response = client.get("/books/abc")
        assert response.status_code == 404
        assert response.is_json


class TestUpdateBook:
    def test_updates_book_and_returns_200(self, client):
        created = client.post("/books", json=make_payload()).get_json()
        response = client.put(
            f"/books/{created['id']}",
            json=make_payload(title="Dune Messiah", year=1969, isbn=None),
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == created["id"]
        assert data["title"] == "Dune Messiah"
        assert data["year"] == 1969
        assert data["isbn"] is None

    def test_returns_404_for_unknown_id(self, client):
        response = client.put("/books/999", json=make_payload())
        assert response.status_code == 404

    def test_rejects_payload_missing_required_fields(self, client):
        created = client.post("/books", json=make_payload()).get_json()
        response = client.put(f"/books/{created['id']}", json={"title": "Only Title"})
        assert response.status_code == 400
        assert "author" in error_details(response)

    def test_rejects_malformed_json_body(self, client):
        created = client.post("/books", json=make_payload()).get_json()
        response = client.put(
            f"/books/{created['id']}", data="{not json", content_type="application/json"
        )
        assert response.status_code == 400

    def test_update_is_visible_on_subsequent_get(self, client):
        created = client.post("/books", json=make_payload()).get_json()
        client.put(f"/books/{created['id']}", json=make_payload(author="Someone Else"))
        response = client.get(f"/books/{created['id']}")
        assert response.get_json()["author"] == "Someone Else"


class TestDeleteBook:
    def test_deletes_book_and_returns_204(self, client):
        created = client.post("/books", json=make_payload()).get_json()
        response = client.delete(f"/books/{created['id']}")
        assert response.status_code == 204
        assert response.get_data() == b""

    def test_deleted_book_is_gone(self, client):
        created = client.post("/books", json=make_payload()).get_json()
        client.delete(f"/books/{created['id']}")
        assert client.get(f"/books/{created['id']}").status_code == 404
        assert client.get("/books").get_json() == []

    def test_returns_404_when_deleting_unknown_id(self, client):
        response = client.delete("/books/999")
        assert response.status_code == 404


class TestErrorHandling:
    def test_unknown_route_returns_json_404(self, client):
        response = client.get("/nope")
        assert response.status_code == 404
        assert response.is_json

    def test_unsupported_method_returns_json_405(self, client):
        response = client.patch("/books")
        assert response.status_code == 405
        assert response.is_json


class TestLifecycle:
    def test_full_crud_lifecycle(self, client):
        created = client.post("/books", json=make_payload()).get_json()
        assert client.get("/books").get_json() == [created]

        updated = client.put(
            f"/books/{created['id']}", json=make_payload(title="Dune (updated)")
        ).get_json()
        assert updated["title"] == "Dune (updated)"

        assert client.delete(f"/books/{created['id']}").status_code == 204
        assert client.get("/books").get_json() == []
        assert client.get(f"/books/{created['id']}").status_code == 404
