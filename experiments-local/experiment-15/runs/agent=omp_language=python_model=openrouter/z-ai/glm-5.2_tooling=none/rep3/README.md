# Book Collection API

A small REST API for managing a book collection, built with **FastAPI** and an
embedded **SQLite** database (Python stdlib `sqlite3`).

## Endpoints

| Method   | Path           | Description                          |
| -------- | -------------- | ------------------------------------ |
| `GET`    | `/health`      | Health / DB reachability probe       |
| `POST`   | `/books`       | Create a book                        |
| `GET`    | `/books`       | List all books (optional `?author=`) |
| `GET`    | `/books/{id}`  | Get a single book                    |
| `PUT`    | `/books/{id}`  | Update a book (partial update)       |
| `DELETE` | `/books/{id}`  | Delete a book                        |

### Book schema

```json
{ "title": "string", "author": "string", "year": 2020, "isbn": "string" }
```

`title` and `author` are **required** and must be non-empty. `year` (0–9999)
and `isbn` are optional.

## Setup

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app:app --reload
```

The API is served at <http://127.0.0.1:8000>. Interactive docs are available at
`/docs` (Swagger UI) and `/redoc`.

The SQLite database file defaults to `books.db` in the working directory;
override with the `BOOKS_DB_PATH` environment variable.

## Tests

```bash
pytest -v
```

Tests run against a fresh temporary SQLite database per test, so they are
hermetic and safe to run in parallel.

## Project layout

```
app.py              # FastAPI application, models, SQLite layer
test_app.py         # pytest integration tests
requirements.txt    # Python dependencies
README.md           # this file
```
