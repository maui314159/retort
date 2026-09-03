"""Unit and integration tests for the book collection API."""


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json() == {"status": "healthy"}


def test_create_book_success(client):
    res = client.post("/books", json=valid_book())
    assert res.status_code == 201
    body = res.get_json()
    assert body["id"] == 1
    assert body["title"] == "1984"
    assert body["author"] == "George Orwell"
    assert body["year"] == 1949
    assert body["isbn"] == "978-0451524935"


def test_create_book_missing_title(client):
    res = client.post("/books", json={"author": "Someone"})
    assert res.status_code == 400
    assert "title is required" in res.get_json()["errors"]


def test_create_book_missing_author(client):
    res = client.post("/books", json={"title": "A Book"})
    assert res.status_code == 400
    assert "author is required" in res.get_json()["errors"]


def test_create_book_invalid_year(client):
    res = client.post("/books", json=valid_book(year="nineteen-eighty"))
    assert res.status_code == 400
    assert "year must be an integer" in res.get_json()["errors"]


def test_list_books_and_filter(client):
    client.post("/books", json=valid_book(title="1984", author="George Orwell"))
    client.post("/books", json=valid_book(title="Animal Farm", author="George Orwell"))
    client.post("/books", json=valid_book(title="Dune", author="Frank Herbert"))

    res = client.get("/books")
    assert res.status_code == 200
    assert len(res.get_json()) == 3

    res = client.get("/books?author=George%20Orwell")
    assert res.status_code == 200
    titles = [b["title"] for b in res.get_json()]
    assert titles == ["1984", "Animal Farm"]


def test_get_book_by_id(client):
    created = client.post("/books", json=valid_book()).get_json()
    res = client.get(f"/books/{created['id']}")
    assert res.status_code == 200
    assert res.get_json()["title"] == "1984"


def test_get_book_not_found(client):
    res = client.get("/books/9999")
    assert res.status_code == 404
    assert res.get_json()["error"] == "book not found"


def test_update_book_success(client):
    created = client.post("/books", json=valid_book()).get_json()
    res = client.put(
        f"/books/{created['id']}",
        json=valid_book(title="Nineteen Eighty-Four", author="G. Orwell", year=1950, isbn="123"),
    )
    assert res.status_code == 200
    body = res.get_json()
    assert body["title"] == "Nineteen Eighty-Four"
    assert body["author"] == "G. Orwell"
    assert body["year"] == 1950


def test_update_book_validation_error(client):
    created = client.post("/books", json=valid_book()).get_json()
    res = client.put(f"/books/{created['id']}", json={"author": "No Title"})
    assert res.status_code == 400


def test_update_book_not_found(client):
    res = client.put("/books/9999", json=valid_book())
    assert res.status_code == 404


def test_delete_book_success(client):
    created = client.post("/books", json=valid_book()).get_json()
    res = client.delete(f"/books/{created['id']}")
    assert res.status_code == 204
    assert res.data == b""
    assert client.get(f"/books/{created['id']}").status_code == 404


def test_delete_book_not_found(client):
    res = client.delete("/books/9999")
    assert res.status_code == 404


def valid_book(**overrides):
    payload = {"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}
    payload.update(overrides)
    return payload
