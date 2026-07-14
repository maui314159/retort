# Books API

A small REST API for managing a book collection, built with **FastAPI** + **SQLite** (stdlib `sqlite3`).

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET    | `/health` | Health check |
| POST   | `/books` | Create a book (`title`, `author` required; `year`, `isbn` optional) |
| GET    | `/books` | List all books; supports `?author=` filter |
| GET    | `/books/{id}` | Get a single book |
| PUT    | `/books/{id}` | Replace a book (`title`, `author` required) |
| DELETE | `/books/{id}` | Delete a book (204 on success) |

Validation: `title` and `author` are required and must not be blank; `year` must be non-negative. Errors return HTTP 422 with details. Missing resources return 404.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install fastapi uvicorn pydantic pytest httpx
```

## Run

```bash
uvicorn app:app --reload --port 8000
```

Then open http://127.0.0.1:8000/docs for the interactive OpenAPI UI.

The SQLite database file (`books.db`) is created automatically on startup. Override with:

```bash
BOOKS_DB_PATH=/tmp/mybooks.db uvicorn app:app
```

## Tests

```bash
pytest -q
```

Tests use an isolated SQLite DB per test (in a temp dir), so they don't touch the dev database.

## Files

- `app.py` — FastAPI app and routes
- `db.py` — SQLite data layer
- `models.py` — Pydantic request models / validation
- `test_app.py` — pytest integration tests covering all endpoints
