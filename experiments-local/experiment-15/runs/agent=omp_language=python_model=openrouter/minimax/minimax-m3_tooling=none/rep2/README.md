# Book Collection REST API

A small REST API for managing a book collection, built with **FastAPI** and
**SQLite**. Provides full CRUD over a `/books` resource, a case-insensitive
author filter, request validation via Pydantic, and a `/health` endpoint.

## Requirements

- Python 3.10+ (developed against 3.12)
- pip

## Setup

```bash
# (Optional) create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Run the server

The server uses SQLite via the `BOOKS_DB` environment variable; it defaults
to `books.db` in the current working directory. The schema is created
automatically on startup.

```bash
# Default: creates ./books.db
uvicorn app:app --host 0.0.0.0 --port 8000

# Or override the database path
BOOKS_DB=/tmp/my-books.db uvicorn app:app --reload
```

Once running, interactive API docs are available at:

- Swagger UI: <http://localhost:8000/docs>
- ReDoc:      <http://localhost:8000/redoc>

## API

| Method | Path             | Description                              | Success |
|--------|------------------|------------------------------------------|---------|
| GET    | `/health`        | Liveness probe                           | `200`   |
| POST   | `/books`         | Create a book                            | `201`   |
| GET    | `/books`         | List books (optional `?author=` filter)  | `200`   |
| GET    | `/books/{id}`    | Fetch a single book                      | `200`   |
| PUT    | `/books/{id}`    | Partial update (only fields in body)     | `200`   |
| DELETE | `/books/{id}`    | Remove a book                            | `204`   |

### Book schema

```json
{
  "id": 1,
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0-7432-7356-5"
}
```

- `title` and `author` are required and must be non-blank strings.
- `year` is optional; when supplied it must satisfy `0 <= year <= 9999`.
- `isbn` is optional and stored as a string up to 32 characters.
- The `?author=` filter matches case-insensitively.

### Error responses

| Status | Meaning                                                                |
|--------|------------------------------------------------------------------------|
| `400`  | Malformed request body or empty update payload                         |
| `404`  | No book exists with the given `id`                                     |
| `422`  | Validation failure (missing required field, blank string, bad year)    |
| `503`  | Database unreachable from `/health`                                    |

## Examples

```bash
# Health check
curl -s http://localhost:8000/health
# {"status":"healthy"}

# Create
curl -s -X POST http://localhost:8000/books \
  -H 'content-type: application/json' \
  -d '{"title":"1984","author":"George Orwell","year":1949,"isbn":"978-0-452-28423-4"}'

# List, filter by author
curl -s 'http://localhost:8000/books?author=george%20orwell'

# Fetch
curl -s http://localhost:8000/books/1

# Update (partial)
curl -s -X PUT http://localhost:8000/books/1 \
  -H 'content-type: application/json' \
  -d '{"year":1950}'

# Delete
curl -s -X DELETE http://localhost:8000/books/1 -o /dev/null -w '%{http_code}\n'
# 204
```

## Tests

The test suite uses `pytest` and FastAPI's `TestClient`. A temporary
SQLite file backs the app and is wiped between tests.

```bash
pytest tests.py -v
```

Coverage includes:

- Health endpoint
- Create (success, optional fields, whitespace trimming, all validation failures)
- List and author filter (exact match, case-insensitive, no match)
- Get (success, 404)
- Update (partial, full, 404, empty body, invalid field)
- Delete (success, 404)
- Full end-to-end CRUD lifecycle

## Project layout

```
.
├── app.py            # FastAPI app, routes, Pydantic models, SQLite helpers
├── tests.py          # pytest test suite
├── requirements.txt  # Runtime + test dependencies
├── README.md         # This file
└── books.db          # Created on first run (gitignored in real projects)
```
