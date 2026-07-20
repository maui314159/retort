# Book Collection API

A REST API service for managing a book collection, built with Python + Flask and backed by SQLite.

## Endpoints

| Method | Path          | Description                              |
| ------ | ------------- | ---------------------------------------- |
| GET    | `/health`     | Health check                             |
| POST   | `/books`      | Create a new book (title, author, year, isbn) |
| GET    | `/books`      | List all books; supports `?author=` filter |
| GET    | `/books/{id}` | Get a single book by ID                  |
| PUT    | `/books/{id}` | Update a book                            |
| DELETE | `/books/{id}` | Delete a book                            |

`title` and `author` are required when creating a book. `year` must be an integer when provided. All responses are JSON with appropriate HTTP status codes (200, 201, 204, 400, 404).

## Setup

Requires Python 3.9+.

```bash
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The server starts on `http://localhost:5000` and creates a `books.db` SQLite file in the current directory. To use a different database file or port, set the `BOOKS_DB` and `PORT` environment variables:

```bash
BOOKS_DB=/path/to/books.db PORT=8080 python app.py
```

Note: on macOS, port 5000 is often occupied by the AirPlay Receiver service — use `PORT` to pick another port if needed.

## Example usage

```bash
# Health check
curl http://localhost:5000/health

# Create a book
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}'

# List all books
curl http://localhost:5000/books

# Filter by author
curl "http://localhost:5000/books?author=Frank%20Herbert"

# Get one book
curl http://localhost:5000/books/1

# Update a book
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"year": 1966}'

# Delete a book
curl -X DELETE http://localhost:5000/books/1
```

## Tests

```bash
pytest -v
```

The test suite covers the health check, CRUD operations, input validation, and the author filter. Tests run against a temporary SQLite database, so they do not touch `books.db`.
