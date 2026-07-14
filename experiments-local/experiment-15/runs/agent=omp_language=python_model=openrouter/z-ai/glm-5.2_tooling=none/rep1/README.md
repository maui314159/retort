# Book Collection REST API

A small REST API for managing a book collection, built with **Flask** and
the Python standard-library **`sqlite3`** module. Data is stored in a
local SQLite database file.

## Requirements

- Python 3.11+
- Flask (see `requirements.txt`)

## Setup

```bash
# (optional) create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# install dependencies
pip install -r requirements.txt
```

## Running the server

```bash
python3 app.py
```

The API listens on `http://0.0.0.0:8000`.

The SQLite database file defaults to `books.db` in the working
directory. Override the path with the `BOOKS_DB_PATH` environment
variable:

```bash
BOOKS_DB_PATH=/tmp/books.db python3 app.py
```

The schema is created automatically on first request (or on startup
when run directly).

## Endpoints

| Method   | Path            | Description                          |
|----------|-----------------|--------------------------------------|
| `GET`    | `/health`       | Health check → `{"status":"healthy"}`|
| `POST`   | `/books`        | Create a book                        |
| `GET`    | `/books`        | List all books (optional `?author=`) |
| `GET`    | `/books/{id}`   | Get a single book                    |
| `PUT`    | `/books/{id}`   | Update a book                        |
| `DELETE` | `/books/{id}`   | Delete a book                        |

### Book fields

```json
{
  "id": 1,
  "title": "The Pragmatic Programmer",
  "author": "Hunt",
  "year": 1999,
  "isbn": "9780201616224"
}
```

`title` and `author` are **required** and must be non-empty strings.
`year` (integer) and `isbn` (string) are optional.

### Status codes

- `200` — success (read / update)
- `201` — created
- `204` — deleted (no body)
- `400` — validation error (body contains `{"error": "..."}`)
- `404` — book not found
- `405` — method not allowed

## Examples

```bash
# create
curl -sX POST localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Clean Code","author":"Martin","year":2008,"isbn":"9780132350884"}'

# list
curl -s localhost:8000/books

# filter by author
curl -s 'localhost:8000/books?author=Martin'

# get one
curl -s localhost:8000/books/1

# update
curl -sX PUT localhost:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Clean Code 2e","author":"Martin","year":2021,"isbn":"9780135957059"}'

# delete
curl -sX DELETE localhost:8000/books/1
```

## Tests

```bash
pip install pytest
pytest -v
```

Tests run against a throwaway SQLite file in a temporary directory, so
they never touch the real `books.db`.
