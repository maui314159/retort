# Book Collection API

A small REST API service for managing a book collection, written in Go using
the standard library `net/http` and SQLite for persistence.

## Requirements

- Go 1.21+ (tested with Go 1.26)
- The SQLite driver is `modernc.org/sqlite` (pure Go, no CGO required)

## Setup & Run

```bash
# from the project directory
go mod download        # fetch dependencies
go run .               # serves on :8080, db file ./books.db
```

Flags:

- `-addr` — HTTP listen address (default `:8080`)
- `-db`   — SQLite database path (default `books.db`, use `:memory:` for in-memory)

Example:

```bash
go run . -addr=:9090 -db=/tmp/books.db
```

Build a binary:

```bash
go build -o bookapi .
./bookapi
```

## Endpoints

| Method   | Path         | Description                              |
|----------|--------------|------------------------------------------|
| `GET`    | `/health`    | Health check (`{"status":"ok"}`)         |
| `POST`   | `/books`     | Create a new book                         |
| `GET`    | `/books`     | List all books (supports `?author=` filter) |
| `GET`    | `/books/{id}`| Get a single book by ID                   |
| `PUT`    | `/books/{id}`| Update a book                             |
| `DELETE` | `/books/{id}`| Delete a book                             |

### Book JSON

```json
{
  "id": 1,
  "title": "The Go Programming Language",
  "author": "Donovan",
  "year": 2015,
  "isbn": "978-0134190440",
  "created_at": "2026-06-20T...",
  "updated_at": "2026-06-20T..."
}
```

### Validation

- `title` and `author` are required on `POST`.
- On `PUT`, omitted fields are left unchanged; provided fields must not be blank.
- Invalid JSON or unknown fields return `400 Bad Request`.
- Missing books return `404 Not Found`.

### Example requests

```bash
# Create
curl -s -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Demo","author":"Ada","year":2020,"isbn":"123"}'

# List with filter
curl -s 'localhost:8080/books?author=Ada'

# Get one
curl -s localhost:8080/books/1

# Update
curl -s -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"New Title"}'

# Delete
curl -s -X DELETE localhost:8080/books/1
```

## Status Codes

- `200 OK` — successful GET/PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — invalid input
- `404 Not Found` — book not found
- `405 Method Not Allowed` — unsupported method
- `500 Internal Server Error` — unexpected failure

## Tests

```bash
go test ./...
go test -v ./...
```

Tests cover:
1. Create → List → Get lifecycle
2. Input validation (missing/blank required fields)
3. Update (partial), Delete, and 404 handling
4. Author filter and the health check endpoint

## Project Layout

```
main.go          # entrypoint, CLI flags, HTTP server bootstrap
server.go        # HTTP handlers, routing, validation, JSON helpers
store.go         # SQLite-backed persistence (Store type)
model.go         # Book / BookInput types
server_test.go   # integration tests over the HTTP layer
```
