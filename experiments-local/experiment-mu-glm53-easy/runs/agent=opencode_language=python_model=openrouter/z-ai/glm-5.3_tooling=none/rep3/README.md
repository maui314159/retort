# Book Collection REST API

A small REST API for managing a book collection, written in Python with
[Flask](https://flask.palletsprojects.com/) and
[SQLite](https://www.sqlite.org/). Books are persisted in a local SQLite
database file.

## Requirements

- Python 3.10+
- pip

## Setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Running the server

```bash
python app.py
```

The service listens on `http://127.0.0.1:5000` by default.

Configuration (environment variables):

| Variable  | Default     | Description                      |
|-----------|-------------|----------------------------------|
| `BOOKS_DB`| `books.db`  | Path of the SQLite database file |
| `HOST`    | `127.0.0.1` | Bind address                     |
| `PORT`    | `5000`      | Listen port                      |

Alternatively, use the Flask CLI (supports `--debug` for auto-reload):

```bash
flask --app app run --debug
```

## API

All request and response bodies are JSON. A book looks like this:

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "978-0441172719"
}
```

`id` is assigned by the server. `year` and `isbn` are optional and may be
`null`; `title` and `author` are required and must be non-empty strings.

### `GET /health`

Health check; also verifies the database is reachable.

- `200` — `{"status": "ok"}`
- `503` — `{"status": "error"}` if the database is unreachable

### `POST /books`

Creates a book and returns it with its assigned `id`.

```bash
curl -X POST http://127.0.0.1:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}'
```

- `201` — the created book
- `400` — validation error

Validation rules:

- `title` — required, non-empty string
- `author` — required, non-empty string
- `year` — optional, integer
- `isbn` — optional, string
- unknown fields are ignored

### `GET /books`

Lists all books, ordered by `id`. The optional `?author=` filter performs a
case-insensitive substring match on the author name.

```bash
curl http://127.0.0.1:5000/books
curl "http://127.0.0.1:5000/books?author=orwell"
```

- `200` — JSON array of books (an empty array when nothing matches)

### `GET /books/{id}`

- `200` — the book
- `404` — `{"error": "Book not found"}`

### `PUT /books/{id}`

Updates a book. Any subset of the writable fields (`title`, `author`,
`year`, `isbn`) may be sent; only the supplied fields are changed.

```bash
curl -X PUT http://127.0.0.1:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"year": 1966}'
```

- `200` — the updated book
- `400` — validation error (same rules as POST, applied to supplied fields)
- `404` — book not found

### `DELETE /books/{id}`

```bash
curl -X DELETE http://127.0.0.1:5000/books/1
```

- `204` — deleted (empty body)
- `404` — book not found

### Errors

Validation failures return `400`:

```json
{
  "error": "Validation failed",
  "details": {
    "title": "title is required"
  }
}
```

Malformed request bodies return `400` with
`{"error": "Request body must be valid JSON"}`. Unknown URLs and
unsupported methods return JSON `404`/`405` responses.

## Running the tests

```bash
pytest
```

The suite contains unit tests for the database layer and integration tests
for every endpoint: create, list, filter, get, update, delete, validation,
and error paths. Tests run against a temporary in-memory database and never
touch `books.db`.

## Project layout

```
app.py             Flask application: routes, validation, error handling
db.py              SQLite data-access layer
tests/             pytest test suite
requirements.txt   Runtime and test dependencies
pytest.ini         pytest configuration
```
