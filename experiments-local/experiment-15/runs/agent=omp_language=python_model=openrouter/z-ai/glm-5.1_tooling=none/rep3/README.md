# Book Collection API

A REST API for managing a book collection, built with FastAPI and SQLite.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --reload
```

The API is available at `http://127.0.0.1:8000`. Interactive docs at `/docs`.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/books` | Create a book |
| GET | `/books` | List all books (supports `?author=` filter) |
| GET | `/books/{id}` | Get a book by ID |
| PUT | `/books/{id}` | Update a book |
| DELETE | `/books/{id}` | Delete a book |

## Examples

```bash
# Create a book
curl -X POST http://127.0.0.1:8000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"9780743273565"}'

# List all books
curl http://127.0.0.1:8000/books

# Filter by author
curl "http://127.0.0.1:8000/books?author=F.%20Scott%20Fitzgerald"

# Update a book
curl -X PUT http://127.0.0.1:8000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"New Title"}'

# Delete a book
curl -X DELETE http://127.0.0.1:8000/books/1
```

## Test

```bash
pytest test_main.py -v
```
