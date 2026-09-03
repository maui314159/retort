# Book Collection API

A small REST API service for managing a book collection, built with **Python 3**, **Flask**, and **SQLite**.

## Endpoints

| Method | Path            | Description                              |
|--------|-----------------|------------------------------------------|
| GET    | `/health`       | Health check                             |
| POST   | `/books`        | Create a book (`title`, `author`, `year`, `isbn`) |
| GET    | `/books`        | List all books (supports `?author=` filter) |
| GET    | `/books/{id}`   | Get a single book by ID                  |
| PUT    | `/books/{id}`   | Update a book (full replacement)         |
| DELETE | `/books/{id}`   | Delete a book                            |

`title` and `author` are required for POST and PUT. `year` must be an integer; `isbn` is a string. Both are optional.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
python app.py
# API available at http://localhost:5000
```

The SQLite database file defaults to `books.db` in the current directory. Override it with:

```bash
BOOKS_DB_PATH=/tmp/mybooks.db python app.py
```

To listen on a different port:

```bash
PORT=8000 python app.py
```

## Example

```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
```

## Tests

```bash
pip install pytest
pytest -v
```
