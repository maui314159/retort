# Book Collection REST API

A small REST service for managing a book collection, built with Flask and
SQLite. Data is persisted in a local SQLite database file.

## Endpoints

| Method   | Path          | Description                          |
|----------|---------------|--------------------------------------|
| GET      | `/health`     | Health check                         |
| POST     | `/books`      | Create a book                        |
| GET      | `/books`      | List all books (supports `?author=`) |
| GET      | `/books/{id}` | Get a single book                    |
| PUT      | `/books/{id}` | Update a book                        |
| DELETE   | `/books/{id}` | Delete a book                        |

### Book schema

```json
{
  "id": 1,
  "title": "The Pragmatic Programmer",
  "author": "Andy Hunt",
  "year": 1999,
  "isbn": "978-0201616224"
}
```

`title` and `author` are required; `year` (integer) and `isbn` (string) are
optional.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
# serving on http://0.0.0.0:5000
```

The SQLite database path defaults to `books.db` in the working directory and
can be overridden with the `BOOKS_DB_PATH` environment variable. The listen
port defaults to `5000` and can be overridden with `PORT`.

## Tests

```bash
pytest -v
```

Tests run against an isolated temporary database per test.

## Example usage

```bash
# Create
curl -sX POST localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Clean Code","author":"Robert C. Martin","year":2008,"isbn":"978-0132350884"}'

# List, filtered by author
curl -s 'localhost:5000/books?author=Robert%20C.%20Martin'

# Update
curl -sX PUT localhost:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year":2009}'

# Delete
curl -sX DELETE localhost:5000/books/1
```
