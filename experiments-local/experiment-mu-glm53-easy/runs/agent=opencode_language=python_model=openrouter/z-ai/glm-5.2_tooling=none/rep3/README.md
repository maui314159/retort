# Book Collection REST API

A small REST API for managing a book collection, built with **Flask** and **SQLite**.

## Requirements

- Python 3.10+
- Flask (install via pip)

## Setup

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install flask
```

## Running the service

```bash
python app.py
```

The server starts on `http://0.0.0.0:5000` (override the port with the `PORT`
environment variable). The SQLite database file defaults to `books.db` in the
working directory; override the path with `BOOKS_DB_PATH`:

```bash
BOOKS_DB_PATH=/tmp/books.db PORT=8080 python app.py
```

The `books` table is created automatically on startup.

## Endpoints

| Method   | Path           | Description                         |
|----------|----------------|-------------------------------------|
| GET      | `/health`      | Health check                        |
| POST     | `/books`       | Create a new book                   |
| GET      | `/books`       | List all books (`?author=` filter)  |
| GET      | `/books/{id}`  | Get a single book by ID             |
| PUT      | `/books/{id}`  | Update a book (partial updates OK)  |
| DELETE   | `/books/{id}`  | Delete a book                       |

### Book schema

```json
{ "id": 1, "title": "...", "author": "...", "year": 2024, "isbn": "..." }
```

`title` and `author` are required on create; `year` and `isbn` are optional.

## Examples

```bash
# Create a book
curl -s -X POST localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Refactoring","author":"Fowler","year":1999,"isbn":"978-0134757599"}'

# List books by author
curl -s 'localhost:5000/books?author=Fowler'

# Update a book (partial)
curl -s -X PUT localhost:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year":2018}'

# Delete a book
curl -s -X DELETE localhost:5000/books/1
```

## Status codes

- `200` — successful GET/PUT
- `201` — successful POST (created)
- `204` — successful DELETE
- `400` — validation error (JSON body with `errors`)
- `404` — book not found

## Running the tests

```bash
pip install pytest
pytest -q
```

Each test runs against a fresh temporary SQLite database.

## Project layout

```
app.py         # Flask application + routes + SQLite layer
test_app.py    # pytest integration tests (5 tests)
README.md
```
