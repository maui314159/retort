import os
import sqlite3
import pytest
from fastapi.testclient import TestClient
from main import app, get_db

TEST_DATABASE_URL = "test_books.db"

def override_get_db():
    conn = sqlite3.connect(TEST_DATABASE_URL)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )
    """)
    conn.commit()
    yield conn

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_and_teardown():
    if os.path.exists(TEST_DATABASE_URL):
        os.remove(TEST_DATABASE_URL)
    yield
    if os.path.exists(TEST_DATABASE_URL):
        os.remove(TEST_DATABASE_URL)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_create_and_get_book():
    book_data = {
        "title": "The Pragmatic Programmer",
        "author": "Andrew Hunt",
        "year": 1999,
        "isbn": "978-0201616224"
    }
    response = client.post("/books", json=book_data)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == book_data["title"]
    assert "id" in data
    
    book_id = data["id"]
    
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 200
    assert response.json()["title"] == book_data["title"]

def test_list_books_with_author_filter():
    client.post("/books", json={"title": "Book 1", "author": "Author A", "year": 2020})
    client.post("/books", json={"title": "Book 2", "author": "Author B", "year": 2021})
    
    response = client.get("/books?author=Author A")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["author"] == "Author A"
    
    response = client.get("/books?author=Author")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

def test_update_book():
    response = client.post("/books", json={"title": "Old Title", "author": "Author", "year": 2000})
    book_id = response.json()["id"]
    
    update_data = {"title": "New Title", "year": 2023}
    response = client.put(f"/books/{book_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New Title"
    assert data["author"] == "Author"
    assert data["year"] == 2023

def test_delete_book():
    response = client.post("/books", json={"title": "To Delete", "author": "Author", "year": 2000})
    book_id = response.json()["id"]
    
    response = client.delete(f"/books/{book_id}")
    assert response.status_code == 204
    
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 404

def test_validation_missing_fields():
    response = client.post("/books", json={"title": "No Author"})
    assert response.status_code == 422