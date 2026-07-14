# Book Collection REST API

A small REST service for managing a book collection, built with Flask and SQLite.

## Endpoints

| Method | Path              | Description                                |
|--------|-------------------|--------------------------------------------|
| GET    | /health           | Health check                               |
| POST   | /books            | Create a book (title, author, year, isbn)   |
| GET    | /books            | List books; supports `?author=` filter    |
| GET    | /books/{id}       | Get a single book                          |
| PUT    | /books/{id}       | Update a book (partial updates supported)  |
| DELETE | /books/{id}       | Delete a book                              |

`title` and `author` are required on create. On update, any field may be
omitted; provided fields must still be non-empty where applicable.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
# serves on http://localhost:8000
```

The SQLite database file defaults to `books.db` in this directory and is
created automatically on startup. Override its location with:

```bash
BOOKS_DB_PATH=/tmp/books.db python app.py
```

## Examples

```bash
# create
curl -X POST http://localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Refactoring","author":"Martin Fowler","year":1999,"isbn":"9780134757999"}'

# list, filtered by author
curl 'http://localhost:8000/books?author=Martin%20Fowler'

# get one
curl http://localhost:8000/books/1

# update
curl -X PUT http://localhost:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year":2020}'

# delete
curl -X DELETE http://localhost:8000/books/1

# health
curl http://localhost:8000/health
```

## Tests

```bash
pytest -v
```

Tests use a temporary SQLite database per test, so they do not touch the
real `books.db`.

## Status codes

- 200 — successful read / update / delete
- 201 — created
- 400 — validation error
- 404 — book not found
