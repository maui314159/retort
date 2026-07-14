# Book Collection REST API

A simple REST API service for managing a book collection, built with Python, FastAPI, and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Input validation for required fields
- SQLite database for data persistence
- Health check endpoint

## Requirements

- Python 3.8+
- pip (Python package manager)

## Installation

1. Clone or download this repository.

2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Running the Application

Start the server with:

```bash
python main.py
```

The API will be available at `http://localhost:8000`.

### Alternative: Using uvicorn directly

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## API Endpoints

### Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "book-collection-api"
}
```

### Create a Book

```
POST /books
```

Request body:
```json
{
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "9780743273565"
}
```

Response (201 Created):
```json
{
  "id": 1,
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "9780743273565"
}
```

**Note**: `title` and `author` are required fields. `year` and `isbn` are optional.

### List All Books

```
GET /books
```

Optional query parameter:
- `author` - Filter by author name (case-insensitive substring match)

Examples:
```
GET /books
GET /books?author=Fitzgerald
```

Response (200 OK):
```json
[
  {
    "id": 1,
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "9780743273565"
  }
]
```

### Get a Single Book

```
GET /books/{id}
```

Response (200 OK):
```json
{
  "id": 1,
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "9780743273565"
}
```

Response (404 Not Found) if book doesn't exist.

### Update a Book

```
PUT /books/{id}
```

Request body (all fields optional):
```json
{
  "title": "Updated Title",
  "year": 2024
}
```

Response (200 OK):
```json
{
  "id": 1,
  "title": "Updated Title",
  "author": "F. Scott Fitzgerald",
  "year": 2024,
  "isbn": "9780743273565"
}
```

Response (404 Not Found) if book doesn't exist.

### Delete a Book

```
DELETE /books/{id}
```

Response (204 No Content) on success.
Response (404 Not Found) if book doesn't exist.

## Running Tests

Run the test suite with pytest:

```bash
pytest test_api.py -v
```

To run tests with coverage:

```bash
pytest test_api.py --cov=. --cov-report=html
```

## Project Structure

```
.
├── main.py           # FastAPI application with endpoints
├── database.py       # SQLite database operations
├── models.py         # Pydantic models for validation
├── test_api.py       # Test suite
├── requirements.txt  # Python dependencies
└── README.md         # This file
```

## Database

The application uses SQLite for data storage. The database file (`books.db`) is created automatically when the application starts.

### Schema

```sql
CREATE TABLE books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT UNIQUE
)
```

## Error Responses

The API returns appropriate HTTP status codes:

- `200 OK` - Request successful
- `201 Created` - Resource created successfully
- `204 No Content` - Resource deleted successfully
- `400 Bad Request` - Invalid input (e.g., duplicate ISBN)
- `404 Not Found` - Resource not found
- `422 Unprocessable Entity` - Validation error (missing required fields)

Example error response:
```json
{
  "detail": "Book not found"
}
```
