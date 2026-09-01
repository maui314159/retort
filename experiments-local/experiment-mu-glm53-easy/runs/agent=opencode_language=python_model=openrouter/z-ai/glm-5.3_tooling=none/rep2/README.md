# Book Collection REST API

A small REST API for managing a book collection, built with Python,
[Flask](https://flask.palletsprojects.com/), and SQLite. Data is stored in a
local SQLite database file (no external services required).

## Requirements

- Python 3.10+
- The packages in `requirements.txt` (Flask and pytest)

## Setup

```bash
python -m venv venv          # a venv/ already exists in this workspace
source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Running the server

```bash
python app.py
# or: flask --app app run --debug
```

The server listens on `http://127.0.0.1:5000`. The SQLite database is created
automatically at `./books.db` on startup. Override the location with the
`BOOKS_DB` environment variable:

```bash
BOOKS_DB=/tmp/my-books.db python app.py
```

## API

| Method   | Path        | Description                              |
| -------- | ----------- | ---------------------------------------- |
| `GET`    | `/health`   | Health check                             |
| `POST`   | `/books`    | Create a book                            |
| `GET`    | `/books`    | List books; supports `?author=` filter   |
| `GET`    | `/books/ID` | Get a single book                        |
| `PUT`    | `/books/ID` | Update a book (partial updates allowed)  |
| `DELETE` | `/books/ID` | Delete a book                            |

### Examples

```bash
# Health check
curl http://127.0.0.1:5000/health

# Create a book
curl -X POST http://127.0.0.1:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}'

# List all books
curl http://127.0.0.1:5000/books

# List books whose author matches (partial, case-insensitive)
curl "http://127.0.0.1:5000/books?author=orwell"

# Get / update / delete a book by id
curl http://127.0.0.1:5000/books/1
curl -X PUT http://127.0.0.1:5000/books/1 -H "Content-Type: application/json" -d '{"year": 1950}'
curl -X DELETE http://127.0.0.1:5000/books/1
```

### Status codes

- `200 OK` — successful read or update
- `201 Created` — book created; the response body is the new book (with `id`)
- `204 No Content` — book deleted
- `400 Bad Request` — validation failure; body is
  `{"error": "validation failed", "fields": {"title": "title is required", ...}}`
- `404 Not Found` — no book with that id (or unknown route)

### Validation rules

- `title` and `author` are **required** on create and must be non-empty strings.
- `year` is optional and must be an integer between 0 and 9999.
- `isbn` is optional and must be a non-empty string.
- On `PUT`, only the fields present in the payload are validated and updated;
  `title`/`author` may not be set to empty values. An empty payload is a `400`.

## Tests

```bash
python -m pytest -v
```

The test suite covers the health check, full CRUD flow, the author filter,
validation failures, and 404 handling (26 test cases). Each test uses an
isolated temporary SQLite database, so the suite never touches `books.db`.

## Project layout

```
app.py            # application, routes, and SQLite access layer
test_app.py       # pytest integration tests (Flask test client)
requirements.txt  # dependencies
books.db          # created at runtime (gitignored)
```
