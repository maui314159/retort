import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from main import app, get_db, Base, BookDB

# Use in-memory SQLite with StaticPool to share the connection
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    # Create tables before each test
    Base.metadata.create_all(bind=engine)
    yield
    # Drop tables after each test
    Base.metadata.drop_all(bind=engine)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_create_and_get_book():
    book_data = {
        "title": "1984",
        "author": "George Orwell",
        "year": 1949,
        "isbn": "978-0451524935"
    }
    response = client.post("/books", json=book_data)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "1984"
    assert "id" in data
    
    book_id = data["id"]
    get_response = client.get(f"/books/{book_id}")
    assert get_response.status_code == 200
    assert get_response.json()["title"] == "1984"

def test_filter_books_by_author():
    client.post("/books", json={"title": "Animal Farm", "author": "George Orwell", "year": 1945})
    client.post("/books", json={"title": "Dune", "author": "Frank Herbert", "year": 1965})
    
    response = client.get("/books?author=George")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Animal Farm"

def test_update_book():
    res = client.post("/books", json={"title": "Old Title", "author": "Old Author"})
    book_id = res.json()["id"]
    
    update_data = {"title": "New Title"}
    response = client.put(f"/books/{book_id}", json=update_data)
    assert response.status_code == 200
    assert response.json()["title"] == "New Title"
    assert response.json()["author"] == "Old Author"

def test_delete_book():
    res = client.post("/books", json={"title": "To Delete", "author": "Someone"})
    book_id = res.json()["id"]
    
    delete_response = client.delete(f"/books/{book_id}")
    assert delete_response.status_code == 204
    
    get_response = client.get(f"/books/{book_id}")
    assert get_response.status_code == 404
