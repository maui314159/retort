# Books Collection REST API

A small Flask + SQLite service for managing a book collection.

## Endpoints

| Method | Path             | Description                                  |
|--------|------------------|----------------------------------------------|
| GET    | `/health`        | Health check                                 |
| POST   | `/books`         | Create a book (`title`, `author` required; `year`, `isbn` optional) |
| GET    | `/books`         | List all books; supports `?author=` filter   |
| GET    | `/books/{id}`    | Get a single book                            |
| PUT    | `/books/{id}`    | Update a book (partial updates supported)    |
| DELETE | `/books/{id}`    | Delete a book                                |

All request and response bodies are JSON. A successful `DELETE` returns `204 No Content`.

### Status codes

- `200` — successful GET/PUT
- `201` — book created
- `204` — book deleted
- `400` — validation error (response body: `{"error": "..."}`)
- `404` — book not found

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
# serves on http://0.0.0.0:5000
```

Alternatively with the Flask CLI:

```bash
flask --app app:create_app run
```

Configuration via environment variables:

- `BOOKS_DB_PATH` — SQLite database file (default: `books.db`)
- `PORT` — listen port (default: `5000`)

## Tests

```bash
pytest -v
```

Tests use an in-memory SQLite database, so they don't touch any on-disk `books.db`.

## Example

```bash
curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

curl 'http://localhost:5000/books?author=Frank%20Herbert'
```
