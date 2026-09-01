# Book Collection REST API

A small, dependency-free REST service for managing a book collection. Built
with the Python standard library (`http.server` + `sqlite3`) — no `pip
install` required.

## Endpoints

| Method   | Path           | Description                          |
|----------|----------------|--------------------------------------|
| GET      | `/health`      | Health check                         |
| GET      | `/books`       | List all books; supports `?author=`  |
| POST     | `/books`       | Create a book                        |
| GET      | `/books/{id}`  | Get a single book                    |
| PUT      | `/books/{id}`  | Update a book                        |
| DELETE   | `/books/{id}`  | Delete a book                        |

### Book shape

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719" }
```

`title` and `author` are required and must be non-empty strings. `year` is an
optional non-negative integer. `isbn` is an optional string.

## Setup

The project ships with a virtualenv that already contains `pytest`. No other
dependencies are needed.

```bash
# from the project root
source venv/bin/activate
```

## Run

```bash
python app.py                  # serves on 127.0.0.1:8000, data in books.db
python app.py --port 9000 --db /tmp/books.db
```

### Examples

```bash
# create
curl -s -X POST localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

# list
curl -s localhost:8000/books
curl -s 'localhost:8000/books?author=Frank%20Herbert'

# update
curl -s -X PUT localhost:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year":1966}'

# delete
curl -s -X DELETE localhost:8000/books/1
```

## Tests

```bash
pytest -q
```

Tests cover the dispatch layer (CRUD, validation, status codes) and a live
HTTP integration test against a started server.

## Layout

- `bookdb.py` — SQLite persistence layer (`BookDB`).
- `app.py` — HTTP server + request dispatcher (`BookAPI`, `BookHTTPRequestHandler`).
- `test_dispatch.py` — unit tests for the dispatch/validation logic.
- `test_http.py` — integration tests over a real socket.
