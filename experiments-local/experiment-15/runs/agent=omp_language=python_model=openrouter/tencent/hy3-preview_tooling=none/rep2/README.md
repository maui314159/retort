# Book Collection REST API

A simple REST API service for managing a book collection, built with Python, FastAPI, and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Input validation for required fields
- SQLite database for data persistence
- Health check endpoint

## API Endpoints

| Method | Endpoint | Description |
|--------|-----------|-------------|
| GET | `/health` | Health check |
| POST | `/books` | Create a new book |
| GET | `/books` | List all books (supports `?author=` filter) |
| GET | `/books/{id}` | Get a single book by ID |
| PUT | `/books/{id}` | Update a book |
| DELETE | `/books/{id}` | Delete a book |

## Book Object

```json
{
  "title": "string (required)",
  "author": "string (required)",
  "year": "integer (optional, 1000-2100)",
  "isbn": "string (optional)"
}
```

## Setup

1. Install Python 3.8 or higher

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

### Development mode with auto-reload:
```bash
uvicorn main:app --reload
```

### Production mode:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Or directly:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

## API Documentation

FastAPI automatically generates interactive API documentation:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Running Tests

```bash
pytest test_api.py -v
```

For test coverage:
```bash
pip install pytest-cov
pytest test_api.py --cov=. --cov-report=html
```

## Example Requests

### Create a book
```bash
curl -X POST "http://localhost:8000/books" \
  -H "Content-Type: application/json" \
  -d '{"title": "1984", "author": "George Orwell", "year": 1949}'
```

### List all books
```bash
curl "http://localhost:8000/books"
```

### Filter by author
```bash
curl "http://localhost:8000/books?author=George"
```

### Get a specific book
```bash
curl "http://localhost:8000/books/1"
```

### Update a book
```bash
curl -X PUT "http://localhost:8000/books/1" \
  -H "Content-Type: application/json" \
  -d '{"title": "1984 (Updated)", "year": 1950}'
```

### Delete a book
```bash
curl -X DELETE "http://localhost:8000/books/1"
```

## Database

The application uses SQLite for data storage. The database file (`books.db`) is created automatically when the application starts.

## Error Responses

The API returns appropriate HTTP status codes:

- `200` - Success
- `201` - Created
- `204` - No Content (successful delete)
- `404` - Not Found
- `422` - Validation Error
- `500` - Internal Server Error
