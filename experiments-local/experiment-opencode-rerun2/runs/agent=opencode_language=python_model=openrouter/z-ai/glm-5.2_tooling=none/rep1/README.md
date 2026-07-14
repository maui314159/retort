# Book Collection API

A small REST API for managing a book collection, built with **FastAPI** and **SQLite**.

## Endpoints

| Method | Path              | Description                          |
|-------|------------------|--------------------------------------|
| GET   | `/health`        | Health check                         |
| POST  | `/books`         | Create a new book (201)               |
| GET   | `/books`         | List all books, supports `?author=`  |
| GET   | `/books/{id}`    | Get a single book (404 if missing)   |
| PUT   | `/books/{id}`    | Update a book (404 if missing)       |
| DELETE| `/books/{id}`    | Delete a book (204, or 404)          |

### Book fields

- `title` *(string, required, non-blank)*
- `author` *(string, required, non-blank)*
- `year` *(integer, optional, 0–9999)*
- `isbn` *(string, optional, ≤ 32 chars)*

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python main.py
# or
uvicorn main:app --reload --port 8000
```

Then open:

- API root / interactive docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

The SQLite database file defaults to `books.db` in the working directory and is
created automatically on startup. Override the path with the `BOOKS_DB_PATH`
environment variable.

### Example

```bash
curl -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937,"isbn":"978-0-00-000000-1"}'

curl http://127.0.0.1:8000/books
curl 'http://127.0.0.1:8000/books?author=J.R.R. Tolkien'
```

## Tests

```bash
pytest -q
```

Tests use FastAPI's `TestClient` and a per-test temporary SQLite database
(isolated via the `BOOKS_DB_PATH` environment variable), so no state leaks
between runs.

## Project layout

```
.
├── main.py              # FastAPI app + SQLite persistence
├── requirements.txt
├── README.md
└── tests/
    └── test_books.py    # health, CRUD, filter, validation
```
