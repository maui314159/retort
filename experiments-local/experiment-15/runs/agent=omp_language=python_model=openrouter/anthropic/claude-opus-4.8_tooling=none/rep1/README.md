# Book Collection API

A small REST service for managing a book collection, built with **FastAPI** and
**SQLite** (via the Python standard library `sqlite3`).

## Requirements

- Python 3.10+

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --reload
```

The API listens on `http://127.0.0.1:8000`. Data is stored in `books.db` in the
working directory (created automatically on first run). Interactive docs are
available at `http://127.0.0.1:8000/docs`.

## Endpoints

| Method | Path           | Description                                  |
|--------|----------------|----------------------------------------------|
| GET    | `/health`      | Health check → `{"status": "ok"}`            |
| POST   | `/books`       | Create a book → `201`                        |
| GET    | `/books`       | List books; optional `?author=` filter       |
| GET    | `/books/{id}`  | Get one book → `404` if missing              |
| PUT    | `/books/{id}`  | Replace a book → `404` if missing            |
| DELETE | `/books/{id}`  | Delete a book → `204`, or `404` if missing   |

### Book fields

| Field    | Type    | Required |
|----------|---------|----------|
| `title`  | string  | yes (non-blank) |
| `author` | string  | yes (non-blank) |
| `year`   | integer | no       |
| `isbn`   | string  | no       |

Invalid input (missing or blank `title`/`author`) returns `422` with validation
details.

### Examples

```bash
# Create
curl -X POST localhost:8000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Herbert","year":1965,"isbn":"978-0441013593"}'

# List, filtered by author
curl 'localhost:8000/books?author=Herbert'

# Get / update / delete
curl localhost:8000/books/1
curl -X PUT localhost:8000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"Dune Messiah","author":"Herbert","year":1969}'
curl -X DELETE localhost:8000/books/1
```

## Tests

```bash
pytest -q
```

The test suite (`test_api.py`) runs against a fresh in-memory SQLite database
and covers health, CRUD, the author filter, validation, and 404 handling.

## Layout

- `main.py` — FastAPI app and route handlers
- `models.py` — Pydantic request/response schemas with validation
- `db.py` — SQLite connection, schema, and transaction helper
- `test_api.py` — integration tests
