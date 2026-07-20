# Book Collection API

A small REST API service for managing a book collection, built with **Flask** and **SQLite**.

## Requirements

- Python 3.10+
- Dependencies: `pip install -r requirements.txt` (Flask + pytest)

## Running the server

```bash
pip install -r requirements.txt
python3 app.py
```

The server starts on **port 8000** by default (override with the `PORT` environment
variable). The SQLite database is created automatically as `books.db` in the current
directory (override with the `BOOKS_DB` environment variable).

## Endpoints

| Method | Path          | Description                              | Success status |
|--------|---------------|------------------------------------------|----------------|
| GET    | `/health`     | Health check                             | 200            |
| POST   | `/books`      | Create a book (`title`, `author` required; `year`, `isbn` optional) | 201 |
| GET    | `/books`      | List all books; filter with `?author=`   | 200            |
| GET    | `/books/{id}` | Get a single book by ID                  | 200            |
| PUT    | `/books/{id}` | Update a book (partial updates allowed)  | 200            |
| DELETE | `/books/{id}` | Delete a book                            | 204            |

### Example

```bash
# Create a book
curl -X POST http://localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}'
# → 201 {"id": 1, "title": "Dune", ...}

# List books by author
curl "http://localhost:8000/books?author=Frank%20Herbert"

# Update a book
curl -X PUT http://localhost:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year": 1966}'

# Delete a book
curl -X DELETE http://localhost:8000/books/1   # → 204 No Content
```

### Validation & error responses

- `title` and `author` are required for POST and must be non-empty strings.
- `year` must be an integer when provided; `isbn` must be a string.
- Invalid payloads return `400` with `{"errors": [...]}`.
- Unknown book IDs return `404` with `{"error": "Book not found"}`.

## Running the tests

```bash
python3 -m pytest test_app.py -v
```

12 integration tests cover the health check, CRUD operations, the `?author=` filter,
input validation, and 404 handling. Each test runs against a fresh temporary SQLite
database, so no cleanup is needed.

## Project layout

- `app.py` — application factory, routes, validation, and SQLite access
- `test_app.py` — pytest integration tests
- `requirements.txt` — Python dependencies
