# Book Collection REST API

A small REST API for managing a book collection, built with **Python / Flask** and **SQLite**.

## Requirements

- Python 3.10+ (developed on 3.12)
- pip

## Setup

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The server listens on `http://127.0.0.1:5000`.

> On macOS, port 5000 can be taken by the AirPlay Receiver. If the port is busy,
> start on another port: `PORT=5001 python app.py`

For auto-reload during development: `flask --app app run --debug`

### Configuration (environment variables)

| Variable        | Default                  | Purpose                          |
|-----------------|--------------------------|----------------------------------|
| `PORT`          | `5000`                   | Server port                      |
| `HOST`          | `127.0.0.1`              | Bind address                     |
| `BOOKS_DB_PATH` | `books.db` (next to app) | SQLite database file             |

The `books` table is created automatically on startup.

## API Reference

| Method | Path         | Description                                 | Success | Errors     |
|--------|--------------|---------------------------------------------|---------|------------|
| GET    | `/health`    | Health check (verifies DB connectivity)     | 200     | 503        |
| POST   | `/books`     | Create a new book                           | 201     | 400        |
| GET    | `/books`     | List all books; `?author=` exact filter     | 200     | —          |
| GET    | `/books/{id}`| Get a single book                           | 200     | 404        |
| PUT    | `/books/{id}`| Replace/update a book                       | 200     | 400, 404   |
| DELETE | `/books/{id}`| Delete a book                               | 204     | 404        |

All responses are JSON. Unknown routes and unsupported methods also return JSON
errors (404 / 405).

### Book object

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "978-0441172719"
}
```

### Validation rules

- `title` — **required**, non-empty string (surrounding whitespace is trimmed)
- `author` — **required**, non-empty string (surrounding whitespace is trimmed)
- `year` — optional integer between 1 and 2200 (a numeric string like `"1965"` is accepted)
- `isbn` — optional non-empty string

`PUT` performs a full replacement: `title` and `author` are required, and any
optional field that is omitted is cleared (set to `null`).

Validation failures return `400` with a structured body:

```json
{
  "error": "Validation failed",
  "details": ["Field 'title' is required."]
}
```

## Examples

```bash
BASE=http://127.0.0.1:5000

curl -s $BASE/health

curl -s -X POST $BASE/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}'

curl -s $BASE/books
curl -s "$BASE/books?author=Frank%20Herbert"
curl -s $BASE/books/1

curl -s -X PUT $BASE/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}'

curl -s -i -X DELETE $BASE/books/1
```

## Tests

```bash
source venv/bin/activate
pytest -v
```

With coverage:

```bash
pytest --cov=app --cov-report=term-missing
```

The suite contains integration tests covering CRUD, the author filter, validation
rules, error handling, and a full lifecycle test. Every test uses its own
temporary SQLite database, so the suite never touches `books.db`.

## Project Layout

```
app.py               Flask app: routes, validation, SQLite access
tests/test_app.py    Integration test suite
requirements.txt     Runtime + test dependencies
pyproject.toml       pytest configuration
conftest.py          Makes the project importable in tests
```

## Implementation Notes

- Storage: SQLite via the standard-library `sqlite3` module (no ORM); all queries
  are parameterised, and connections are opened per request and closed on
  teardown.
- `GET /health` executes `SELECT 1` against the database and returns
  `{"status": "ok"}` (503 if the database is unreachable).
- `POST /books` sets a `Location` header pointing at the new resource.
- The author filter is an exact (case-sensitive) match; an empty or omitted
  `author` parameter returns all books.
