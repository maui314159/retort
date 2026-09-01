# Books REST API

A REST API service for managing a book collection, built with Python + Flask and backed by SQLite.

## Features

- Create, read, update, and delete books
- Filter the book list by author
- Input validation (title and author are required)
- JSON responses with appropriate HTTP status codes
- Health check endpoint

## Requirements

- Python 3.10+

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The server starts on `http://127.0.0.1:5000`. Alternatively:

```bash
flask --app app run --port 5000
```

The SQLite database is created automatically. Its location defaults to `books.db` in the current directory and can be overridden with the `BOOKS_DB` environment variable:

```bash
BOOKS_DB=/tmp/books.db python app.py
```

## API Endpoints

| Method | Path            | Description                          | Success | Errors   |
|--------|-----------------|--------------------------------------|---------|----------|
| GET    | `/health`       | Health check                         | 200     |          |
| POST   | `/books`        | Create a book                        | 201     | 400      |
| GET    | `/books`        | List all books (`?author=` filter)   | 200     |          |
| GET    | `/books/{id}`   | Get a single book                    | 200     | 404      |
| PUT    | `/books/{id}`   | Replace/update a book                | 200     | 400, 404 |
| DELETE | `/books/{id}`   | Delete a book                        | 204     | 404      |

A book has the following fields:

- `title` (string, required)
- `author` (string, required)
- `year` (integer, optional)
- `isbn` (string, optional)

Validation rules: `title` and `author` must be non-empty strings; `year`, when provided, must be an integer; `isbn`, when provided, must be a string. Violations return `400` with an `{"error": "..."}` body. Unknown fields are ignored. The `author` filter matches case-insensitively as a substring.

### Examples

Create a book:

```bash
curl -X POST http://127.0.0.1:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "9780451524935"}'
```

List books, optionally filtered by author:

```bash
curl http://127.0.0.1:5000/books
curl "http://127.0.0.1:5000/books?author=orwell"
```

Get one book:

```bash
curl http://127.0.0.1:5000/books/1
```

Update a book (full replacement; `title` and `author` are required):

```bash
curl -X PUT http://127.0.0.1:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Nineteen Eighty-Four", "author": "George Orwell", "year": 1949}'
```

Delete a book:

```bash
curl -X DELETE http://127.0.0.1:5000/books/1
```

Health check:

```bash
curl http://127.0.0.1:5000/health
```

## Tests

```bash
pytest
```

The test suite covers the health check, CRUD operations, author filtering, validation errors, and 404 handling. Each test uses an isolated temporary database.

## Project Layout

- `app.py` — Flask application (routes, validation, error handling)
- `db.py` — SQLite connection and schema helpers
- `test_app.py` — pytest integration tests
- `requirements.txt` — dependencies
