import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app(str(tmp_path / "books.db"))
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def create_book(client, **overrides):
    payload = {"title": "1984", "author": "George Orwell", "year": 1949,
               "isbn": "978-0451524935"}
    payload.update(overrides)
    return client.post("/books", json=payload)


class TestHealth:
    def test_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.get_json() == {"status": "ok"}


class TestCreateBook:
    def test_returns_201_with_created_book(self, client):
        response = create_book(client)
        assert response.status_code == 201
        body = response.get_json()
        assert body["id"] == 1
        assert body["title"] == "1984"
        assert body["author"] == "George Orwell"
        assert body["year"] == 1949
        assert body["isbn"] == "978-0451524935"
        assert body["created_at"] is not None

    @pytest.mark.parametrize("missing", ["title", "author"])
    def test_requires_title_and_author(self, client, missing):
        payload = {"title": "1984", "author": "George Orwell"}
        payload.pop(missing)
        response = client.post("/books", json=payload)
        assert response.status_code == 400
        assert missing in response.get_json()["fields"]

    @pytest.mark.parametrize("empty", ["", "   "])
    def test_rejects_blank_title(self, client, empty):
        response = create_book(client, title=empty)
        assert response.status_code == 400
        assert "title" in response.get_json()["fields"]

    @pytest.mark.parametrize("bad_year", ["nineteen-eighty-four", 1949.5, True, 10000, -1])
    def test_rejects_invalid_year(self, client, bad_year):
        response = create_book(client, year=bad_year)
        assert response.status_code == 400
        assert "year" in response.get_json()["fields"]

    @pytest.mark.parametrize(
        "raw_body, content_type",
        [("not json at all", "text/plain"), ("[1, 2, 3]", "application/json")],
    )
    def test_rejects_non_object_body(self, client, raw_body, content_type):
        response = client.post("/books", data=raw_body, content_type=content_type)
        assert response.status_code == 400
        assert "error" in response.get_json()


class TestListBooks:
    def test_empty_collection_returns_empty_list(self, client):
        response = client.get("/books")
        assert response.status_code == 200
        assert response.get_json() == []

    def test_lists_all_created_books(self, client):
        create_book(client)
        create_book(client, title="The Left Hand of Darkness",
                    author="Ursula K. Le Guin", year=1969)
        response = client.get("/books")
        assert response.status_code == 200
        assert [book["title"] for book in response.get_json()] == \
            ["1984", "The Left Hand of Darkness"]

    def test_author_filter_is_partial_and_case_insensitive(self, client):
        create_book(client, author="Ursula K. Le Guin")
        create_book(client, title="A Wizard of Earthsea",
                    author="le guin admirer")
        create_book(client, title="Animal Farm", author="George Orwell")
        response = client.get("/books", query_string={"author": "LE GUIN"})
        assert response.status_code == 200
        assert sorted(book["author"] for book in response.get_json()) == \
            ["Ursula K. Le Guin", "le guin admirer"]

    def test_author_filter_with_no_match_returns_empty_list(self, client):
        create_book(client)
        response = client.get("/books", query_string={"author": "Nobody"})
        assert response.status_code == 200
        assert response.get_json() == []


class TestGetBook:
    def test_returns_book_by_id(self, client):
        create_book(client)
        response = client.get("/books/1")
        assert response.status_code == 200
        assert response.get_json()["id"] == 1

    def test_unknown_id_returns_404(self, client):
        response = client.get("/books/999")
        assert response.status_code == 404
        assert response.get_json() == {"error": "book not found"}

    def test_non_numeric_id_returns_404(self, client):
        response = client.get("/books/abc")
        assert response.status_code == 404
        assert "error" in response.get_json()


class TestUpdateBook:
    def test_partial_update(self, client):
        create_book(client)
        response = client.put("/books/1", json={"year": 1950})
        assert response.status_code == 200
        body = response.get_json()
        assert body["year"] == 1950
        assert body["title"] == "1984"
        assert body["author"] == "George Orwell"

    def test_unknown_id_returns_404(self, client):
        response = client.put("/books/999", json={"year": 1950})
        assert response.status_code == 404
        assert response.get_json() == {"error": "book not found"}

    def test_rejects_blank_title(self, client):
        create_book(client)
        response = client.put("/books/1", json={"title": "  "})
        assert response.status_code == 400
        assert "title" in response.get_json()["fields"]

    def test_rejects_empty_payload(self, client):
        create_book(client)
        response = client.put("/books/1", json={})
        assert response.status_code == 400
        assert response.get_json()["error"] == "no valid fields to update"


class TestDeleteBook:
    def test_delete_then_book_is_gone(self, client):
        create_book(client)
        response = client.delete("/books/1")
        assert response.status_code == 204
        assert response.data == b""
        assert client.get("/books/1").status_code == 404

    def test_unknown_id_returns_404(self, client):
        response = client.delete("/books/999")
        assert response.status_code == 404
        assert response.get_json() == {"error": "book not found"}
