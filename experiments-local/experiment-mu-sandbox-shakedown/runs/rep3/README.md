# Books REST API

A simple REST API for managing a book collection, built entirely with the
**Python standard library** (no third-party dependencies). Data is stored in
an embedded **SQLite** database.

## Requirements

- Python 3.10+ (only the standard library is used by the service itself)
- [pytest](https://pytest.org) to run the test suite (optional; the tests also
  run with `python -m unittest`)

## Setup & Run

```bash
python app.py
```

The server listens on `http://0.0.0.0:8000` by default. Configure with
environment variables:

| Variable   | Default              | Description                      |
|------------|----------------------|----------------------------------|
| `HOST`     | `0.0.0.0`            | Bind address                     |
| `PORT`     | `8000`               | Bind port                        |
| `BOOKS_DB` | `books.db` (next to `app.py`) | SQLite database file    |

The SQLite schema is created automatically on startup.

## API

| Method   | Path           | Description                        |
|----------|----------------|------------------------------------|
| `GET`    | `/health`      | Health check                       |
| `GET`    | `/books`       | List all books (`?author=` filter) |
| `POST`   | `/books`       | Create a book                      |
| `GET`    | `/books/{id}`  | Get a single book                  |
| `PUT`    | `/books/{id}`  | Update a book                      |
| `DELETE` | `/books/{id}`  | Delete a book                      |

A book has the fields `title`, `author`, `year` (optional integer) and
`isbn` (optional string). **`title` and `author` are required** and must be
non-empty strings.

### Status codes

- `200` — success (GET/PUT)
- `201` — book created (POST), includes a `Location` header
- `204` — book deleted (DELETE)
- `400` — validation error, missing/invalid JSON body
- `404` — book or path not found
- `405` — method not allowed for an existing path

### Examples

```bash
# Health check
curl http://localhost:8000/health

# Create a book
curl -X POST http://localhost:8000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}'

# List all books
curl http://localhost:8000/books

# List books filtered by author
curl "http://localhost:8000/books?author=Frank%20Herbert"

# Get one book
curl http://localhost:8000/books/1

# Update a book
curl -X PUT http://localhost:8000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}'

# Delete a book
curl -X DELETE http://localhost:8000/books/1
```

### Example responses

```json
// GET /books/1 -> 200
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}

// POST /books with missing author -> 400
{"errors": ["'author' is required."]}
```

## Tests

```bash
pytest -v            # or: python -m unittest discover -v
```

The suite includes unit tests for the storage and validation layers plus
integration tests that run the real HTTP server and exercise every endpoint.
