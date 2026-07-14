# Book Collection REST API

A small REST API service for managing a book collection, written in Python with FastAPI and SQLite.

## Endpoints

| Method | Path              | Description                          |
|--------|-------------------|--------------------------------------|
| GET    | `/health`         | Health check                         |
| POST   | `/books`          | Create a book (title, author, year, isbn) |
| GET    | `/books`          | List all books (optional `?author=`)  |
| GET    | `/books/{id}`     | Get a single book by ID              |
| PUT    | `/books/{id}`     | Update a book                        |
| DELETE | `/books/{id}`     | Delete a book                        |

`title` and `author` are required (non-empty strings). `year` and `isbn` are optional.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --reload --port 8000
# or
python main.py
```

Then open http://localhost:127.0.0.1:8000/docs for the interactive Swagger UI.

The SQLite database file defaults to `books.db` in the working directory and is
created automatically on startup. Override the location with the `BOOKS_DB_PATH`
environment variable.

## Tests

```bash
pytest -q
```

Tests use an isolated temporary SQLite database per test session (via the
`BOOKS_DB_PATH` env var and `tmp_path`), so they never touch the real `books.db`.

## Status Codes

- `200` — success on read / update / list
- `201` — book created
- `204` — book deleted
- `404` — book not found
- `422` — input validation failed
