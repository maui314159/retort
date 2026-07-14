# Book Collection API

A small REST API for managing a book collection, built with Flask and SQLite.

## Requirements

- Python 3.8+
- Install dependencies:

```bash
pip install -r requirements.txt
```

## Running

```bash
python app.py
```

The server starts on `http://0.0.0.0:5000`. A SQLite database file `books.db`
is created automatically in the current directory on first run.

## Endpoints

| Method   | Path           | Description                          |
|----------|----------------|--------------------------------------|
| GET      | /health        | Health check                         |
| POST     | /books         | Create a new book                    |
| GET      | /books         | List all books (`?author=` filter)   |
| GET      | /books/{id}    | Get a single book by ID              |
| PUT      | /books/{id}    | Update a book (partial updates ok)   |
| DELETE   | /books/{id}    | Delete a book                        |

### Book fields

```json
{
  "id": 1,
  "title": "Refactoring",
  "author": "Martin Fowler",
  "year": 1999,
  "isbn": "0-201-48567-2"
}
```

`title` and `author` are required on create. `year` (integer) and `isbn`
(string) are optional. All fields are optional on PUT (partial updates).

### Status codes

- `200` — successful GET / PUT
- `201` — successful POST
- `204` — successful DELETE
- `400` — validation error (JSON body `{"errors": [...]}`)
- `404` — book not found

## Examples

```bash
# Create
curl -X POST localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Refactoring","author":"Martin Fowler","year":1999,"isbn":"123"}'

# List with filter
curl 'localhost:5000/books?author=Martin%20Fowler'

# Update
curl -X PUT localhost:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Refactoring (2nd ed.)"}'

# Delete
curl -X DELETE localhost:5000/books/1
```

## Tests

```bash
pip install -r requirements.txt
pytest -v
```

Tests use a temporary SQLite database per run and do not touch `books.db`.
