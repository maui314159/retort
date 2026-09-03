# Books API

A small REST API for managing a book collection, built with **Flask** and
**SQLite**. Books have a `title`, `author`, `year`, and `isbn` and are persisted
in a local SQLite database file (`books.db` by default).

## Endpoints

| Method   | Path            | Description                          |
| -------- | --------------- | ------------------------------------ |
| `GET`    | `/health`       | Health check (`{"status": "ok"}`)   |
| `POST`   | `/books`        | Create a new book                    |
| `GET`    | `/books`        | List all books (`?author=` filter)   |
| `GET`    | `/books/{id}`   | Get a single book by ID              |
| `PUT`    | `/books/{id}`   | Update a book                        |
| `DELETE` | `/books/{id}`   | Delete a book                        |

### Request body (`POST` / `PUT`)

```json
{
  "title": "The Hobbit",
  "author": "J.R.R. Tolkien",
  "year": 1937,
  "isbn": "978-0261102217"
}
```

`title` and `author` are **required** (non-empty strings). `year` is an
optional non-negative integer; `isbn` is an optional string. `PUT` merges the
supplied fields with the existing record, so partial updates are supported.

### Status codes

- `200` — successful `GET`, `PUT`
- `201` — book created
- `204` — book deleted (empty body)
- `400` — validation error (JSON `error`/`details`)
- `404` — book not found

## Setup

Requires Python 3.10+.

```bash
python -m venv .venv && source .venv/bin/activate   # optional
pip install -r requirements.txt
```

## Run

```bash
python app.py
# or: flask --app app run --port 5000
```

The API is served at `http://127.0.0.1:5000`. The SQLite database file
(`books.db`) is created automatically on startup.

### Quick examples

```bash
# Health check
curl http://127.0.0.1:5000/health

# Create a book
curl -X POST http://127.0.0.1:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937}'

# List books, optionally filtered by author
curl 'http://127.0.0.1:5000/books?author=J.R.R.%20Tolkien'

# Update a book (partial)
curl -X PUT http://127.0.0.1:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year":1938}'

# Delete a book
curl -X DELETE http://127.0.0.1:5000/books/1
```

## Tests

Tests use Flask's built-in test client with an isolated temp SQLite database
per test.

```bash
pip install pytest
pytest -v
```

Lint with ruff:

```bash
ruff check .
```

## Project layout

```
.
├── app.py              # Flask application (routes, storage, validation)
├── conftest.py         # pytest import bootstrap
├── requirements.txt    # dependencies
├── README.md
└── tests/
    └── test_books.py   # integration tests
```
