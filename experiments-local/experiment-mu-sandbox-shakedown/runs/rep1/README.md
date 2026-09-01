# Books REST API

A small REST API service for managing a book collection, built entirely
with the **Python standard library** (no third-party dependencies):
`http.server` for HTTP and `sqlite3` for embedded storage.

## Requirements

- Python 3.8+ (developed on 3.12)
- No third-party packages required

## Setup and run

```bash
# optional: choose port and database location via environment variables
export PORT=8000            # default: 8000
export BOOKS_DB=books.db    # default: ./books.db

python3 app.py
```

The API is then available at `http://localhost:8000`.

## Endpoints

| Method   | Path           | Description                          | Success |
|----------|----------------|--------------------------------------|---------|
| `GET`    | `/health`      | Health check                         | 200     |
| `POST`   | `/books`       | Create a book                        | 201     |
| `GET`    | `/books`       | List books (`?author=` filter)       | 200     |
| `GET`    | `/books/{id}`  | Get a single book                    | 200     |
| `PUT`    | `/books/{id}`  | Replace/update a book                | 200     |
| `DELETE` | `/books/{id}`  | Delete a book                        | 204     |

Errors are returned as `{"error": "..."}` with status `400` (invalid
input), `404` (not found), or `405` (method not allowed).

### Validation rules

- `title` and `author` are **required**, non-empty strings (for both
  create and update).
- `year` is optional and must be a JSON integer.
- `isbn` is optional and must be a string.
- Unknown fields are ignored.

### Example usage with curl

```bash
# Health check
curl http://localhost:8000/health

# Create a book
curl -X POST http://localhost:8000/books \
     -H "Content-Type: application/json" \
     -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}'

# List all books
curl http://localhost:8000/books

# List books filtered by author (case-insensitive substring match)
curl "http://localhost:8000/books?author=herbert"

# Get a single book
curl http://localhost:8000/books/1

# Update a book (full replacement; title and author required)
curl -X PUT http://localhost:8000/books/1 \
     -H "Content-Type: application/json" \
     -d '{"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}'

# Delete a book
curl -X DELETE http://localhost:8000/books/1
```

## Tests

The integration tests boot a real server on an ephemeral port backed by
a temporary SQLite database, so no cleanup is needed:

```bash
python3 -m pytest -v
```

## Project structure

```
app.py         # API implementation (routing, validation, SQLite store)
test_app.py    # pytest integration tests
README.md      # this file
requirements.txt  # empty: standard library only
```
