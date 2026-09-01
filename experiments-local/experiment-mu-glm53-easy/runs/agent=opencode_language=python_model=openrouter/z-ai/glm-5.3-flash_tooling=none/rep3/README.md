# Book Collection REST API

A small REST service for managing a book collection, built entirely with the
Python standard library — `http.server` for HTTP and `sqlite3` for storage.
No third-party runtime dependencies.

## Requirements

- Python 3.10+ (developed and tested on 3.12)

## Setup & Run

```bash
python3 app.py
```

The server listens on `http://0.0.0.0:8000` by default. Configuration via
environment variables:

| Variable   | Default                  | Description            |
|------------|--------------------------|------------------------|
| `PORT`     | `8000`                   | TCP port to listen on  |
| `HOST`     | `0.0.0.0`                | Interface to bind      |
| `BOOKS_DB` | `books.db` (project dir) | SQLite database file   |

Example with custom settings:

```bash
PORT=9000 BOOKS_DB=/tmp/library.db python3 app.py
```

The SQLite schema is created automatically on startup; data persists across
restarts.

## API

| Method   | Path          | Success            | Errors |
|----------|---------------|--------------------|--------|
| `GET`    | `/health`     | `200`              | — |
| `GET`    | `/books`      | `200`              | — |
| `POST`   | `/books`      | `201` (+ `Location`) | `400` |
| `GET`    | `/books/{id}` | `200`              | `404` |
| `PUT`    | `/books/{id}` | `200`              | `400`, `404` |
| `DELETE` | `/books/{id}` | `204` (no body)    | `404` |
| other    | —             | —                  | `404` (unknown path), `405` (method not allowed) |

### Book fields

| Field    | Type    | Required | Notes |
|----------|---------|----------|-------|
| `title`  | string  | yes (create) | non-empty; surrounding whitespace is trimmed |
| `author` | string  | yes (create) | non-empty; surrounding whitespace is trimmed |
| `year`   | integer | no       | digit strings are accepted and normalized (`"1965"` → `1965`); `null` clears it |
| `isbn`   | string  | no       | numeric values are coerced to strings; `null` clears it |

`PUT /books/{id}` accepts any subset of the fields and updates only the
provided ones. Unknown fields in the payload are ignored. Malformed JSON,
non-object bodies, missing/blank `title`/`author`, or an invalid `year` are
rejected with `400` and a JSON `{"error": "..."}` body.

### Example session (curl)

```bash
# Health check
curl http://localhost:8000/health

# Create a book
curl -X POST http://localhost:8000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}'

# List all books
curl http://localhost:8000/books

# List books filtered by author (case-insensitive substring match)
curl "http://localhost:8000/books?author=herbert"

# Get one book
curl http://localhost:8000/books/1

# Update a book (any subset of fields)
curl -X PUT http://localhost:8000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"year": 1976}'

# Delete a book
curl -X DELETE http://localhost:8000/books/1
```

## Tests

The suite (28 tests) covers the HTTP API end to end — a real server is started
on an ephemeral port for each test — plus unit tests for the storage layer and
validation logic.

```bash
python3 -m pip install -r requirements.txt   # installs pytest
python3 -m pytest -v
```

## Project layout

```
app.py               HTTP server, routing, validation, SQLite store
conftest.py          Makes the repo root importable for pytest
tests/test_api.py    Integration tests over real HTTP
tests/test_store.py  Unit tests for BookStore and validate_book_payload
requirements.txt     Test-only dependencies (runtime is stdlib-only)
```
