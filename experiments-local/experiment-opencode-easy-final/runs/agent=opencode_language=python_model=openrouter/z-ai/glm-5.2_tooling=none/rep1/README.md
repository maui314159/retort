# Books REST API

A small REST API for managing a book collection, built with Flask and SQLite.

## Requirements

- Python 3.9+
- Flask

Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the service

From the project directory:

```bash
python app.py
```

The API listens on `http://127.0.0.1:8000`. On first run it creates a
`books.db` SQLite file in the current directory. The DB path can be
overridden with the `BOOKS_DB_PATH` environment variable.

To reset the database, delete `books.db` and restart the service.

## Endpoints

| Method   | Path             | Description                          |
|---------|-------------------|--------------------------------------|
| GET     | /health           | Health check                         |
| POST    | /books            | Create a book (title, author, year, isbn) |
| GET     | /books            | List all books (`?author=` filter)   |
| GET     | /books/{id}       | Get a single book                    |
| PUT     | /books/{id}       | Update a book                        |
| DELETE  | /books/{id}       | Delete a book                        |

`title` and `author` are required. `year` (integer, 0..9999) and `isbn`
(string) are optional. Validation errors return HTTP 400. Missing books
return HTTP 404.

### Example

```bash
curl -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937,"isbn":"9780261102217"}'

curl http://127.0.0.1:8000/books?author=J.R.R.%20Tolkien
```

## Tests

Run the test suite with pytest:

```bash
pytest -v
```

Tests use a per-run temporary SQLite file, so they don't touch your real
`books.db`.
