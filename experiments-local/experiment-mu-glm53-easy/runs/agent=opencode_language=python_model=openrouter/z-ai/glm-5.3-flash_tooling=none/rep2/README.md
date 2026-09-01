# Books REST API

A REST API service for managing a book collection, built with **Python +
Flask** and backed by **SQLite** (Python's built-in `sqlite3` module — no
external database required).

## Endpoints

| Method   | Path              | Description                              | Success | Errors      |
| -------- | ----------------- | ---------------------------------------- | ------- | ----------- |
| `GET`    | `/health`         | Health check                             | `200`   | —           |
| `POST`   | `/books`          | Create a book                            | `201`   | `400`       |
| `GET`    | `/books`          | List all books (`?author=` filter)       | `200`   | —           |
| `GET`    | `/books/{id}`     | Get a single book                        | `200`   | `404`       |
| `PUT`    | `/books/{id}`     | Update (replace) a book                  | `200`   | `400`, `404`|
| `DELETE` | `/books/{id}`     | Delete a book                            | `204`   | `404`       |

### Book resource shape

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "978-0441172719"
}
```

## Setup

Requires Python 3.9+.

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
```

## Run

```bash
python app.py
# or equivalently:
flask --app app run
```

The service listens on `http://127.0.0.1:5000` by default.

Configuration via environment variables:

| Variable   | Default            | Description                          |
| ---------- | ------------------ | ------------------------------------ |
| `HOST`     | `127.0.0.1`        | Bind address (used by `python app.py`) |
| `PORT`     | `5000`             | Bind port (used by `python app.py`)  |
| `DATABASE` | `./books.db`       | Path to the SQLite database file     |

## Example requests

```bash
# Health check
curl http://127.0.0.1:5000/health

# Create a book
curl -X POST http://127.0.0.1:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}'

# List all books
curl http://127.0.0.1:5000/books

# List books filtered by author (case-insensitive substring match)
curl "http://127.0.0.1:5000/books?author=herbert"

# Get one book
curl http://127.0.0.1:5000/books/1

# Update a book (full replacement)
curl -X PUT http://127.0.0.1:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}'

# Delete a book
curl -X DELETE http://127.0.0.1:5000/books/1
```

## Validation rules

- `title` — required, non-empty string (whitespace is trimmed)
- `author` — required, non-empty string (whitespace is trimmed)
- `year` — optional integer (accepts an int or a numeric string such as `"1965"`)
- `isbn` — optional string
- Unknown fields are ignored

Invalid input returns `400` with a JSON error body:

```json
{
  "error": "Validation failed",
  "details": ["'author' is required and must be a non-empty string"]
}
```

Notes:

- `PUT` replaces the entire resource: fields omitted from the payload
  (`year`, `isbn`) are cleared (set to `null`).
- Errors are always JSON (including 404/405): `{"error": ..., "details": [...]}`
- Non-numeric IDs such as `/books/abc` return `404`.

## Tests

```bash
python -m pytest -v
```

The suite includes unit tests for the validation logic and HTTP-level
integration tests for every endpoint (each test runs against a fresh
temporary SQLite database).

## Project structure

```
app.py                   Flask app: routes, validation, error handlers, app factory
db.py                    SQLite persistence layer (schema + CRUD helpers)
conftest.py              pytest fixtures (test client with isolated database)
tests/test_books.py      Integration tests (HTTP-level)
tests/test_validation.py Unit tests for payload validation
requirements.txt         Runtime dependencies (Flask)
requirements-dev.txt     Development dependencies (pytest)
```
