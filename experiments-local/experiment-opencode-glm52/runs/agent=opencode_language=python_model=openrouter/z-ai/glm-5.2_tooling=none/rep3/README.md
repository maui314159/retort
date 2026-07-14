# Book Collection API

A small REST API service for managing a book collection, built with **FastAPI** and **SQLite**.

## Endpoints

| Method | Path             | Description                        |
|--------|------------------|------------------------------------|
| GET    | `/health`        | Health check                       |
| POST   | `/books`         | Create a new book                  |
| GET    | `/books`         | List all books (`?author=` filter) |
| GET    | `/books/{id}`    | Get a single book                  |
| PUT    | `/books/{id}`    | Update a book                      |
| DELETE | `/books/{id}`    | Delete a book                      |

### Book payload

```json
{
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441172719"
}
```

`title` and `author` are required and must not be blank. `year` (0–9999) and `isbn` (≤ 32 chars) are optional.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python main.py
# or
uvicorn main:app --reload --port 8000
```

The API is served at <http://localhost:8000>. Interactive docs are available at <http://localhost:8000/docs>.

By default data is stored in `books.db` in the working directory. Override with:

```bash
BOOKS_DB_PATH=/path/to/books.db python main.py
```

## Tests

```bash
pytest -v
```

The test suite covers health check, CRUD operations, validation, filtering, and 404 handling. Each test uses an isolated temporary SQLite database.
