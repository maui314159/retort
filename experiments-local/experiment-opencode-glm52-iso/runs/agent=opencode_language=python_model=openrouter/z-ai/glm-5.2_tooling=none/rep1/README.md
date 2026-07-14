# Book Collection REST API

A small Flask service for managing a book collection, backed by SQLite.

## Requirements

- Python 3.10+
- Flask (and stdlib `sqlite3`)

Install dependencies (Flask and pytest are already installed in this
environment, but for a fresh setup):

```bash
pip install flask pytest
```

## Running

```bash
python app.py
```

The server listens on `0.0.0.0:5000` by default. Override the port with
the `PORT` environment variable, and the database path with
`BOOKS_DB_PATH` (defaults to `books.db` in the working directory).

## Endpoints

| Method | Path             | Description                         |
|--------|------------------|-------------------------------------|
| GET    | `/health`        | Health check                        |
| POST   | `/books`         | Create a book (title, author, year, isbn) |
| GET    | `/books`         | List books; supports `?author=` filter |
| GET    | `/books/{id}`    | Get a single book                   |
| PUT    | `/books/{id}`    | Update a book (partial updates OK)  |
| DELETE | `/books/{id}`    | Delete a book                       |

### Example

```bash
curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

curl 'http://localhost:5000/books?author=Frank%20Herbert'
```

`title` and `author` are required on create; both must be non-empty.
`year` must be an integer when provided.

## Tests

```bash
pytest -v
```

Tests use a temporary database per run, so they do not touch the
production `books.db` file.
