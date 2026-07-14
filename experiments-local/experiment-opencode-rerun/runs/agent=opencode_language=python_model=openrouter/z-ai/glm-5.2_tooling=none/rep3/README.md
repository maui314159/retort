# Book Collection REST API

A simple REST API service for managing a book collection, written in Python with Flask and SQLite.

## Requirements

- Python 3.10+
- Flask 3.0+ (see `requirements.txt`)

Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the service

```bash
python app.py
```

The API is served at `http://127.0.0.1:8000`. A SQLite database file `books.db`
is created automatically in the project directory on first run. Override the
database location with the `BOOKS_DB_PATH` environment variable.

## Endpoints

| Method | Path           | Description                              |
|--------|----------------|------------------------------------------|
| GET    | `/health`      | Health check                             |
| POST   | `/books`       | Create a book (title, author, year, isbn)|
| GET    | `/books`       | List all books; supports `?author=` filter|
| GET    | `/books/{id}`  | Get a single book                        |
| PUT    | `/books/{id}`  | Update a book (any subset of fields)     |
| DELETE | `/books/{id}`  | Delete a book                            |

`title` and `author` are required on create and must be non-empty on update.
`year` must be an integer when provided.

### Status codes

- `200` — success (GET, PUT)
- `201` — created (POST)
- `204` — no content (DELETE)
- `400` — validation error (JSON `{"errors": [...]}`)
- `404` — book not found

### Example

```bash
curl -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

curl 'http://127.0.0.1:8000/books?author=Frank%20Herbert'
```

## Tests

```bash
pip install -r requirements.txt
pytest -v
```

Tests use an isolated temporary SQLite database per test run.
