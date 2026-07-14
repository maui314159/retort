# Book Collection REST API

A simple REST API for managing a book collection, built with Flask and SQLite.

## Requirements

- Python 3.10+
- Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the service

```bash
python app.py
```

The server starts on `http://0.0.0.0:8000`. The SQLite database file defaults to
`books.db` in the current directory; override it with the `BOOKS_DB_PATH`
environment variable.

## Endpoints

| Method   | Path           | Description                          |
|----------|----------------|--------------------------------------|
| GET      | `/health`      | Health check                         |
| POST     | `/books`       | Create a book                        |
| GET      | `/books`       | List books (optional `?author=`)     |
| GET      | `/books/{id}`  | Get a single book                    |
| PUT      | `/books/{id}`  | Update a book (partial updates ok)   |
| DELETE   | `/books/{id}`  | Delete a book                        |

### Book payload

```json
{
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441172719"
}
```

`title` and `author` are required on creation. `year` (0–9999) and `isbn`
(string) are optional. PUT supports partial updates.

### Status codes

- `200` — success (GET, PUT)
- `201` — created (POST)
- `204` — no content (DELETE)
- `400` — validation error
- `404` — book not found

## Tests

```bash
pytest -v
```

Tests use a temporary SQLite database per test run.
