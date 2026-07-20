# Book Collection API

A REST API service for managing a book collection, built with **Flask** and **SQLite**.

## Features

- `POST /books` — Create a new book (`title`, `author` required; `year`, `isbn` optional) → `201`
- `GET /books` — List all books; supports `?author=` exact-match filter → `200`
- `GET /books/{id}` — Get a single book by ID → `200` / `404`
- `PUT /books/{id}` — Update (replace) a book → `200` / `404` / `400`
- `DELETE /books/{id}` — Delete a book → `204` / `404`
- `GET /health` — Health check (verifies the database is reachable) → `200`

All responses are JSON. Invalid input (missing/blank `title` or `author`) returns `400`.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
# or: flask --app app run
```

The API listens on http://127.0.0.1:8000 (Flask's default is port 5000).
Data is stored in `books.db` in the working directory; override with the
`BOOKS_DB` environment variable.

### Example

```bash
curl -X POST http://127.0.0.1:8000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}'

curl "http://127.0.0.1:8000/books?author=Frank%20Herbert"
```

## Tests

```bash
pytest
```

Each test runs against a fresh temporary SQLite database, so no state leaks between tests.
