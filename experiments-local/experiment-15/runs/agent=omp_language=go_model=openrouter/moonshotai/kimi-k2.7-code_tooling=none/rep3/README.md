# Book Collection REST API

A small Go REST API for managing a book collection, backed by SQLite.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/books` | Create a new book |
| GET | `/books` | List all books (optional `?author=` filter) |
| GET | `/books/{id}` | Get a single book |
| PUT | `/books/{id}` | Update a book |
| DELETE | `/books/{id}` | Delete a book |

## Requirements

- [Go](https://go.dev/) 1.23 or later

## Run

```bash
go run .
```

The server starts on `http://localhost:8080` and stores data in `books.db`.

## Test

```bash
go test ./...
```

## Example usage

```bash
# Health check
curl http://localhost:8080/health

# Create a book
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Go Programming Language","author":"Alan Donovan","year":2015,"isbn":"978-0134190440"}'

# List books
curl http://localhost:8080/books

# Filter by author
curl "http://localhost:8080/books?author=Donovan"

# Get a book by id (replace 1 with the actual id)
curl http://localhost:8080/books/1

# Update a book
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Go Programming Language","author":"Alan Donovan","year":2016,"isbn":"978-0134190440"}'

# Delete a book
curl -X DELETE http://localhost:8080/books/1
```
