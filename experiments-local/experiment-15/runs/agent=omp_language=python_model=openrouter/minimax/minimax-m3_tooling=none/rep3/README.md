# Book Collection API

A small REST API for managing a book collection. Built with **FastAPI** and **SQLite** (via SQLAlchemy).

## Endpoints

| Method | Path             | Description                                      | Success | Errors              |
| ------ | ---------------- | ------------------------------------------------ | ------- | ------------------- |
| GET    | `/health`        | Health check                                     | 200     | —                   |
| POST   | `/books`         | Create a book                                    | 201     | 422 (validation)    |
| GET    | `/books`         | List books; `?author=` for case-insensitive filter | 200   | —                   |
| GET    | `/books/{id}`    | Fetch one book                                   | 200     | 404                 |
| PUT    | `/books/{id}`    | Replace a book                                   | 200     | 404, 422            |
| DELETE | `/books/{id}`    | Remove a book                                    | 204     | 404                 |

### Request body (`POST` / `PUT`)

```json
{
  "title":  "Dune",
  "author": "Frank Herbert",
  "year":   1965,
  "isbn":   "978-0441172719"
}
```

`title` and `author` are required. `year` (1–9999) and `isbn` (≤32 chars) are optional.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

The SQLite database file (`books.db`) is created in the project root on first
startup. To point the app at a different location, set the `DATABASE_URL`
environment variable (e.g. `DATABASE_URL=sqlite:///./data/books.db`).

Open the auto-generated docs at <http://127.0.0.1:8000/docs>.

### Example requests

```bash
curl -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'

curl 'http://127.0.0.1:8000/books?author=frank'

curl http://127.0.0.1:8000/books/1

curl -X PUT http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune (2nd ed.)","author":"Frank Herbert","year":1965}'

curl -X DELETE http://127.0.0.1:8000/books/1 -i
```

## Tests

```bash
python3 -m pytest tests/ -v
```

The test suite spins up an isolated in-memory SQLite database per test and
exercises the live FastAPI app via `fastapi.testclient.TestClient`, covering
create / read / list / filter / update / delete, validation, and 404 paths.
