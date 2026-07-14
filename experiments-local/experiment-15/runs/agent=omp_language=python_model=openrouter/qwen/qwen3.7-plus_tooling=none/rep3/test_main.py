import os
import pytest
from fastapi.testclient import TestClient

os.environ["DB_PATH"] = "test_books.db"
from main import app, init_db, get_db

@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app) as c:
        yield c
    if os.path.exists("test_books.db"):
        os.remove("test_books.db")

@pytest.fixture(autouse=True)
def clean_db():
    with get_db() as conn:
        conn.execute("DELETE FROM books")
        conn.commit()
    yield

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_create_and_get_book(client):
    book_data = {"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "1234567890"}
    response = client.post("/books", json=book_data)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "1984"
    assert "id" in data
    
    book_id = data["id"]
    get_response = client.get(f"/books/{book_id}")
    assert get_response.status_code == 200
    assert get_response.json()["title"] == "1984"

def test_list_books_with_filter(client):
    client.post("/books", json={"title": "Book 1", "author": "Alice", "year": 2020})
    client.post("/books", json={"title": "Book 2", "author": "Bob", "year": 2021})
    
    response = client.get("/books?author=Alice")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["author"] == "Alice"

def test_update_book(client):
    response = client.post("/books", json={"title": "Old Title", "author": "Author", "year": 2000})
    book_id = response.json()["id"]
    
    update_data = {"title": "New Title", "year": 2023}
    put_response = client.put(f"/books/{book_id}", json=update_data)
    assert put_response.status_code == 200
    assert put_response.json()["title"] == "New Title"
    assert put_response.json()["year"] == 2023
    assert put_response.json()["author"] == "Author"

def test_delete_book(client):
    response = client.post("/books", json={"title": "To Delete", "author": "Author", "year": 2000})
    book_id = response.json()["id"]
    
    del_response = client.delete(f"/books/{book_id}")
    assert del_response.status_code == 204
    
    get_response = client.get(f"/books/{book_id}")
    assert get_response.status_code == 404

def test_validation_error(client):
    response = client.post("/books", json={"title": "No Author"})
    assert response.status_code == 422

def test_not_found(client):
    response = client.get("/books/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Book not found"
