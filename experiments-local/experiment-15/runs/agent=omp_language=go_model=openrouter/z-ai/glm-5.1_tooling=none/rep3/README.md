# Book Collection API

A REST API for managing a book collection, written in Go with SQLite storage.

## Setup

Requires Go 1.22+.

```bash
go mod download
```

## Run

```bash
go run .
```

The server starts on `http://localhost:8080`.

## Endpoints

| Method | Path            | Description              |
|--------|-----------------|--------------------------|
| GET    | /health         | Health check             |
| POST   | /books          | Create a new book        |
| GET    | /books          | List all books           |
| GET    | /books/{id}     | Get a book by ID         |
| PUT    | /books/{id}     | Update a book            |
| DELETE | /books/{id}     | Delete a book            |

### Query Parameters

- `GET /books?author=<name>` — Filter books by author

### Book JSON

```json
{
  "title": "The Go Programming Language",
  "author": "Donovan & Kernighan",
  "year": 2015,
  "isbn": "978-0134190440"
}
```

`title` and `author` are required. `year` and `isbn` are optional.

## Test

```bash
go test -v ./...
```

## Example Requests

```bash
# Health check
curl http://localhost:8080/health

# Create a book
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Go Programming Language","author":"Donovan & Kernighan","year":2015,"isbn":"978-0134190440"}'

# List all books
curl http://localhost:8080/books

# Filter by author
curl "http://localhost:8080/books?author=Donovan%20%26%20Kernighan"

# Get a book
curl http://localhost:8080/books/1

# Update a book
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated Title","author":"New Author"}'

# Delete a book
curl -X DELETE http://localhost:8080/books/1
```
