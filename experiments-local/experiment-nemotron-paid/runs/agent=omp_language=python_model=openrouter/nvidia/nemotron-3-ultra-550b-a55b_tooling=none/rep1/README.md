# Book Collection API

A REST API service for managing a book collection, built with FastAPI and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Input validation (title and author required)
- ISBN uniqueness validation
- Health check endpoint
- JSON responses with appropriate HTTP status codes

## Requirements

- Python 3.10+
- pip

## Installation

1. Clone or navigate to the project directory
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the Application

Start the development server:

```bash
uvicorn main:app --reload
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive API Docs (Swagger UI)**: http://localhost:8000/docs
- **Alternative API Docs (ReDoc)**: http://localhost:8000/redoc

## API Endpoints

### Health Check
- `GET /health` - Returns service health status

### Books
- `POST /books` - Create a new book
- `GET /books` - List all books (supports `?author=` filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book

## Request/Response Examples

### Create a Book

```bash
curl -X POST http://localhost:8000/books   -H "Content-Type: application/json"   -d '{
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "9780743273565"
  }'
```

**Response (201 Created)**:
```json
{
  "id": 1,
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "9780743273565",
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T10:30:00"
}
```

### List All Books

```bash
curl http://localhost:8000/books
```

### Filter Books by Author

```bash
curl "http://localhost:8000/books?author=Fitzgerald"
```

### Get a Single Book

```bash
curl http://localhost:8000/books/1
```

### Update a Book

```bash
curl -X PUT http://localhost:8000/books/1   -H "Content-Type: application/json"   -d '{"title": "The Great Gatsby (Updated)", "year": 1926}'
```

### Delete a Book

```bash
curl -X DELETE http://localhost:8000/books/1
```

## Running Tests

```bash
pytest test_main.py -v
```

Or run with coverage:

```bash
pytest test_main.py -v --cov=main --cov=models
```

## Project Structure

```
.
├── main.py           # FastAPI application with endpoints
├── models.py         # Database models and Pydantic schemas
├── test_main.py      # Integration tests
├── requirements.txt  # Python dependencies
└── README.md         # This file
```

## Data Model

### Book
- `id` (integer, primary key)
- `title` (string, required, max 255 chars)
- `author` (string, required, max 255 chars)
- `year` (integer, optional, 0-9999)
- `isbn` (string, optional, unique, 10-17 digits)
- `created_at` (datetime, auto-generated)
- `updated_at` (datetime, auto-updated)

## Validation Rules

- `title` and `author` are required fields
- `year` must be between 0 and 9999
- `isbn` must be 10-17 digits (if provided)
- `isbn` must be unique across all books

## HTTP Status Codes

- `200 OK` - Successful GET, PUT
- `201 Created` - Successful POST
- `204 No Content` - Successful DELETE
- `404 Not Found` - Resource not found
- `409 Conflict` - ISBN already exists
- `422 Unprocessable Entity` - Validation error
