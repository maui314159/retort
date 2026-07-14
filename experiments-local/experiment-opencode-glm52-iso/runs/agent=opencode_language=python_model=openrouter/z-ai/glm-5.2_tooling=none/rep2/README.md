# Book Collection API

A REST API service for managing a book collection, built with **FastAPI** and **SQLite**.

## Requirements

- Python 3.10+
- Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the service

```bash
uvicorn app:app --reload
```

The API is served at `http://127.0.0.1:8000`. Interactive docs (Swagger UI) are
available at `http://127.0.0.1:8000/docs`.

The SQLite database file `books.db` is created automatically in the working
directory on first startup.

## Endpoints

| Method   | Path           | Description                          |
|----------|----------------|--------------------------------------|
| GET      | `/health`      | Health check                         |
| POST     | `/books`       | Create a book                        |
| GET      | `/books`       | List books (optional `?author=`)     |
| GET      | `/books/{id}`  | Get a single book                    |
| PUT      | `/books/{id}`  | Update a book (partial updates ok)   |
| DELETE   | `/books/{id}`  | Delete a book                        |

### Book schema

```json
{ "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978..." }
```

`title` and `author` are required and must be non-blank. `year` and `isbn` are
optional. PUT updates accept any subset of fields.

### Example

```bash
curl -X POST http://127.0.0.1:8000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

curl "http://127.0.0.1:8000/books?author=Frank%20Herbert"
```

## Tests

```bash
pytest -v
```

Tests use an isolated temporary SQLite database per test, so the real
`books.db` is never touched.
