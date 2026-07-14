# Book Collection API

A REST API service for managing a book collection, built with **FastAPI** and **SQLite**.

## Features

- Create, list, get, update, and delete books
- Filter books by author via `?author=`
- Input validation (title and author are required)
- SQLite persistence
- Health check endpoint

## Requirements

- Python 3.9+
- Dependencies listed in `requirements.txt`

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

The API will be available at http://127.0.0.1:8000.

Interactive API docs (Swagger UI) are served at http://127.0.0.1:8000/docs.

## Endpoints

| Method   | Path           | Description                       |
|----------|----------------|-----------------------------------|
| GET      | `/health`      | Health check                      |
| POST     | `/books`       | Create a new book                 |
| GET      | `/books`       | List all books (supports `?author=`)|
| GET      | `/books/{id}`  | Get a single book by ID           |
| PUT      | `/books/{id}`  | Update a book                     |
| DELETE   | `/books/{id}`  | Delete a book                     |

### Book shape

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "978-0441172719"
}
```

`title` and `author` are required and must be non-empty. `year` and `isbn` are optional.

## Tests

```bash
pytest -v
```

## Storage

Books are stored in a SQLite file `books.db` (created automatically at startup).
