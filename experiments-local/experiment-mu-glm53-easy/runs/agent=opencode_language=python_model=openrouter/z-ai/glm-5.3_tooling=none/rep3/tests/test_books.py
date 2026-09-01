"""Integration and unit tests for the book collection REST API."""

from db import Database

BOOK = {
    "title": "Dune",
    "author": "Frank Herbert",
    "year": 1965,
    "isbn": "978-0441172719",
}


def create_book(client, **overrides):
    payload = dict(BOOK)
    payload.update(overrides)
    return client.post("/books", json=payload)


class TestHealth:
    def test_returns_ok_status(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.get_json() == {"status": "ok"}


class TestCreateBook:
    def test_creates_book_and_returns_201(self, client):
        response = create_book(client)
        assert response.status_code == 201
        assert response.get_json() == {"id": 1, **BOOK}

    def test_year_and_isbn_are_optional(self, client):
        response = client.post(
            "/books", json={"title": "The Hobbit", "author": "J. R. R. Tolkien"}
        )
        assert response.status_code == 201
        body = response.get_json()
        assert body["title"] == "The Hobbit"
        assert body["year"] is None
        assert body["isbn"] is None

    def test_missing_title_is_rejected(self, client):
        response = client.post("/books", json={"author": "Frank Herbert"})
        assert response.status_code == 400
        assert response.get_json() == {
            "error": "Validation failed",
            "details": {"title": "title is required"},
        }

    def test_missing_author_is_rejected(self, client):
        response = client.post("/books", json={"title": "Dune"})
        assert response.status_code == 400
        assert "author" in response.get_json()["details"]

    def test_blank_title_is_rejected(self, client):
        response = create_book(client, title="   ")
        assert response.status_code == 400
        assert "title" in response.get_json()["details"]

    def test_non_string_title_is_rejected(self, client):
        response = create_book(client, title=42)
        assert response.status_code == 400
        assert "title" in response.get_json()["details"]

    def test_non_integer_year_is_rejected(self, client):
        response = create_book(client, year="nineteen eighty-four")
        assert response.status_code == 400
        assert "year" in response.get_json()["details"]

    def test_boolean_year_is_rejected(self, client):
        response = create_book(client, year=True)
        assert response.status_code == 400
        assert "year" in response.get_json()["details"]

    def test_non_string_isbn_is_rejected(self, client):
        response = create_book(client, isbn=12345)
        assert response.status_code == 400
        assert "isbn" in response.get_json()["details"]

    def test_invalid_json_body_is_rejected(self, client):
        response = client.post(
            "/books", data="not json", content_type="application/json"
        )
        assert response.status_code == 400
        assert "error" in response.get_json()

    def test_non_object_json_body_is_rejected(self, client):
        response = client.post(
            "/books", data="[1, 2, 3]", content_type="application/json"
        )
        assert response.status_code == 400
        assert "error" in response.get_json()

    def test_missing_body_is_rejected(self, client):
        response = client.post("/books")
        assert response.status_code == 400


class TestListBooks:
    def test_empty_collection_returns_empty_list(self, client):
        response = client.get("/books")
        assert response.status_code == 200
        assert response.get_json() == []

    def test_lists_all_books_in_creation_order(self, client):
        create_book(client)
        create_book(client, title="1984", author="George Orwell", year=1949)
        response = client.get("/books")
        assert response.status_code == 200
        books = response.get_json()
        assert [book["id"] for book in books] == [1, 2]
        assert [book["title"] for book in books] == ["Dune", "1984"]

    def test_author_filter_matches_case_insensitively(self, client):
        create_book(client)
        create_book(client, title="1984", author="George Orwell", year=1949)
        response = client.get("/books", query_string={"author": "frank herbert"})
        assert response.status_code == 200
        books = response.get_json()
        assert len(books) == 1
        assert books[0]["author"] == "Frank Herbert"

    def test_author_filter_matches_partial_names(self, client):
        create_book(client)
        create_book(client, title="1984", author="George Orwell", year=1949)
        response = client.get("/books", query_string={"author": "orwell"})
        assert [book["author"] for book in response.get_json()] == ["George Orwell"]

    def test_author_filter_with_no_match_returns_empty_list(self, client):
        create_book(client)
        response = client.get("/books", query_string={"author": "Nobody"})
        assert response.status_code == 200
        assert response.get_json() == []

    def test_empty_author_param_returns_all_books(self, client):
        create_book(client)
        response = client.get("/books", query_string={"author": ""})
        assert response.status_code == 200
        assert len(response.get_json()) == 1


class TestGetBook:
    def test_returns_book_by_id(self, client):
        created = create_book(client).get_json()
        response = client.get(f"/books/{created['id']}")
        assert response.status_code == 200
        assert response.get_json() == created

    def test_missing_book_returns_404(self, client):
        response = client.get("/books/999")
        assert response.status_code == 404
        assert response.get_json() == {"error": "Book not found"}

    def test_non_integer_id_returns_404(self, client):
        response = client.get("/books/abc")
        assert response.status_code == 404
        assert "error" in response.get_json()


class TestUpdateBook:
    def test_updates_single_field(self, client):
        created = create_book(client).get_json()
        response = client.put(f"/books/{created['id']}", json={"year": 1966})
        assert response.status_code == 200
        body = response.get_json()
        assert body["year"] == 1966
        assert body["title"] == created["title"]
        assert body["author"] == created["author"]

    def test_updates_all_fields(self, client):
        created = create_book(client).get_json()
        payload = {
            "title": "Dune Messiah",
            "author": "F. Herbert",
            "year": 1969,
            "isbn": "978-0441172696",
        }
        response = client.put(f"/books/{created['id']}", json=payload)
        assert response.status_code == 200
        assert response.get_json() == {"id": created["id"], **payload}

    def test_missing_book_returns_404(self, client):
        response = client.put("/books/999", json={"title": "Nope"})
        assert response.status_code == 404
        assert response.get_json() == {"error": "Book not found"}

    def test_blank_title_is_rejected(self, client):
        created = create_book(client).get_json()
        response = client.put(f"/books/{created['id']}", json={"title": "  "})
        assert response.status_code == 400
        assert "title" in response.get_json()["details"]

    def test_invalid_year_is_rejected(self, client):
        created = create_book(client).get_json()
        response = client.put(f"/books/{created['id']}", json={"year": "x"})
        assert response.status_code == 400
        assert "year" in response.get_json()["details"]

    def test_empty_object_leaves_book_unchanged(self, client):
        created = create_book(client).get_json()
        response = client.put(f"/books/{created['id']}", json={})
        assert response.status_code == 200
        assert response.get_json() == created

    def test_unknown_fields_are_ignored(self, client):
        created = create_book(client).get_json()
        response = client.put(
            f"/books/{created['id']}", json={"publisher": "Chilton Books"}
        )
        assert response.status_code == 200
        assert response.get_json() == created

    def test_invalid_json_body_is_rejected(self, client):
        created = create_book(client).get_json()
        response = client.put(
            f"/books/{created['id']}",
            data="not json",
            content_type="application/json",
        )
        assert response.status_code == 400


class TestDeleteBook:
    def test_deletes_book_and_returns_204(self, client):
        created = create_book(client).get_json()
        response = client.delete(f"/books/{created['id']}")
        assert response.status_code == 204
        assert response.get_data() == b""
        assert client.get(f"/books/{created['id']}").status_code == 404

    def test_missing_book_returns_404(self, client):
        response = client.delete("/books/999")
        assert response.status_code == 404
        assert response.get_json() == {"error": "Book not found"}

    def test_deleting_twice_returns_404(self, client):
        created = create_book(client).get_json()
        client.delete(f"/books/{created['id']}")
        response = client.delete(f"/books/{created['id']}")
        assert response.status_code == 404


class TestApiContract:
    def test_unknown_route_returns_json_404(self, client):
        response = client.get("/nope")
        assert response.status_code == 404
        assert response.content_type.startswith("application/json")

    def test_unsupported_method_returns_json_405(self, client):
        response = client.patch("/books/1")
        assert response.status_code == 405
        assert response.content_type.startswith("application/json")

    def test_responses_use_json_content_type(self, client):
        created = create_book(client).get_json()
        for path in ("/health", "/books", f"/books/{created['id']}"):
            response = client.get(path)
            assert response.content_type.startswith("application/json")


class TestDatabaseLayer:
    def test_crud_roundtrip(self):
        db = Database(":memory:")
        try:
            book = db.create_book("Dune", "Frank Herbert", 1965, "978-0441172719")
            assert book == {
                "id": 1,
                "title": "Dune",
                "author": "Frank Herbert",
                "year": 1965,
                "isbn": "978-0441172719",
            }
            assert db.get_book(1) == book
            assert db.list_books() == [book]

            updated = db.update_book(1, {"year": 1966})
            assert updated["year"] == 1966

            assert db.delete_book(1) is True
            assert db.get_book(1) is None
            assert db.list_books() == []
        finally:
            db.close()

    def test_update_missing_book_returns_none(self):
        db = Database(":memory:")
        try:
            assert db.update_book(42, {"title": "Ghost"}) is None
        finally:
            db.close()

    def test_delete_missing_book_returns_false(self):
        db = Database(":memory:")
        try:
            assert db.delete_book(42) is False
        finally:
            db.close()
