import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from models import Base, Book, get_db

# Test database setup
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def cleanup_db():
    # Clean up database before each test
    db = TestingSessionLocal()
    try:
        db.query(Book).delete()
        db.commit()
    finally:
        db.close()


class TestHealthCheck:
    async def test_health_check(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestCreateBook:
    async def test_create_book_success(self, client: AsyncClient):
        book_data = {
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "year": 1925,
            "isbn": "9780743273565"
        }
        response = await client.post("/books", json=book_data)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == book_data["title"]
        assert data["author"] == book_data["author"]
        assert data["year"] == book_data["year"]
        assert data["isbn"] == book_data["isbn"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_create_book_missing_title(self, client: AsyncClient):
        book_data = {
            "author": "F. Scott Fitzgerald",
            "year": 1925
        }
        response = await client.post("/books", json=book_data)
        assert response.status_code == 422

    async def test_create_book_missing_author(self, client: AsyncClient):
        book_data = {
            "title": "The Great Gatsby",
            "year": 1925
        }
        response = await client.post("/books", json=book_data)
        assert response.status_code == 422

    async def test_create_book_duplicate_isbn(self, client: AsyncClient):
        book_data = {
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "year": 1925,
            "isbn": "9780743273565"
        }
        # Create first book
        response1 = await client.post("/books", json=book_data)
        assert response1.status_code == 201
        
        # Try to create second book with same ISBN
        book_data2 = book_data.copy()
        book_data2["title"] = "Another Title"
        response2 = await client.post("/books", json=book_data2)
        assert response2.status_code == 409
        assert "ISBN" in response2.json()["detail"]


class TestListBooks:
    async def test_list_books_empty(self, client: AsyncClient):
        response = await client.get("/books")
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_books_with_data(self, client: AsyncClient):
        # Create a book first
        book_data = {
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "year": 1925,
            "isbn": "9780743273565"
        }
        await client.post("/books", json=book_data)
        
        response = await client.get("/books")
        assert response.status_code == 200
        books = response.json()
        assert len(books) == 1
        assert books[0]["title"] == "The Great Gatsby"

    async def test_list_books_filter_by_author(self, client: AsyncClient):
        # Create books with different authors
        await client.post("/books", json={
            "title": "Book 1",
            "author": "Author A",
            "year": 2000
        })
        await client.post("/books", json={
            "title": "Book 2",
            "author": "Author B",
            "year": 2001
        })
        await client.post("/books", json={
            "title": "Book 3",
            "author": "Author A",
            "year": 2002
        })
        
        response = await client.get("/books?author=Author A")
        assert response.status_code == 200
        books = response.json()
        assert len(books) == 2
        for book in books:
            assert "Author A" in book["author"]


class TestGetBook:
    async def test_get_book_success(self, client: AsyncClient):
        # Create a book first
        create_response = await client.post("/books", json={
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "year": 1925,
            "isbn": "9780743273565"
        })
        book_id = create_response.json()["id"]
        
        response = await client.get(f"/books/{book_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book_id
        assert data["title"] == "The Great Gatsby"

    async def test_get_book_not_found(self, client: AsyncClient):
        response = await client.get("/books/999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Book not found"


class TestUpdateBook:
    async def test_update_book_success(self, client: AsyncClient):
        # Create a book first
        create_response = await client.post("/books", json={
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "year": 1925
        })
        book_id = create_response.json()["id"]
        
        # Update the book
        update_data = {
            "title": "The Great Gatsby (Updated)",
            "year": 1926
        }
        response = await client.put(f"/books/{book_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "The Great Gatsby (Updated)"
        assert data["year"] == 1926
        assert data["author"] == "F. Scott Fitzgerald"  # Unchanged

    async def test_update_book_not_found(self, client: AsyncClient):
        response = await client.put("/books/999", json={"title": "New Title"})
        assert response.status_code == 404

    async def test_update_book_duplicate_isbn(self, client: AsyncClient):
        # Create first book
        await client.post("/books", json={
            "title": "Book 1",
            "author": "Author 1",
            "isbn": "9780743273565"
        })
        
        # Create second book
        create_response2 = await client.post("/books", json={
            "title": "Book 2",
            "author": "Author 2",
            "isbn": "9780743273566"
        })
        book_id2 = create_response2.json()["id"]
        
        # Try to update second book with first book's ISBN
        response = await client.put(f"/books/{book_id2}", json={"isbn": "9780743273565"})
        assert response.status_code == 409


class TestDeleteBook:
    async def test_delete_book_success(self, client: AsyncClient):
        # Create a book first
        create_response = await client.post("/books", json={
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "year": 1925
        })
        book_id = create_response.json()["id"]
        
        # Delete the book
        response = await client.delete(f"/books/{book_id}")
        assert response.status_code == 204
        
        # Verify it's deleted
        get_response = await client.get(f"/books/{book_id}")
        assert get_response.status_code == 404

    async def test_delete_book_not_found(self, client: AsyncClient):
        response = await client.delete("/books/999")
        assert response.status_code == 404
