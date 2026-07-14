# bookapi

A small REST API service for managing a book collection, written in Go using
only the standard library (`net/http`) and an embedded SQLite database
([`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite), a pure-Go
driver — no CGO required).

## Features

- `POST   /books`       — Create a new book (`title`, `author`, `year`, `isbn`)
- `GET    /books`       — List all books (supports `?author=` filter)
- `GET    /books/{id}`  — Get a single book by ID
- `PUT    /books/{id}`  — Update a book
- `DELETE /books/{id}`  — Delete a book
- `GET    /health`      — Health check

Responses are JSON with appropriate HTTP status codes (`201 Created`,
`200 OK`, `204 No Content`, `400 Bad Request`, `404 Not Found`,
`500 Internal Server Error`). `title` and `author` are required and validated.

## Requirements

- Go 1.22 or newer (uses the enhanced `ServeMux` pattern routing)

## Setup & run

```bash
# from the repository root
go mod download
go run ./cmd/bookapi
```

By default the server listens on `:8080` and stores data in `./books.db`.
Both can be overridden via flags or environment variables:

```bash
ADDR=:9090 DB_PATH=/tmp/books.db go run ./cmd/bookapi
# or
go run ./cmd/bookapi -addr :9090 -db /tmp/books.db
```

To build a standalone binary:

```bash
go build -o bookapi ./cmd/bookapi
./bookapi
```

## Example usage

```bash
# Create
curl -s -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937,"isbn":"978-0261102217"}'

# List all
curl -s localhost:8080/books

# List by author
curl -s 'localhost:8080/books?author=J.R.R.%20Tolkien'

# Get one (replace 1 with the id returned by create)
curl -s localhost:8080/books/1

# Update
curl -s -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1938,"isbn":"978-0261102217"}'

# Delete
curl -s -X DELETE localhost:8080/books/1

# Health
curl -s localhost:8080/health
```

## Project layout

```
cmd/bookapi/main.go          # entrypoint: wires store + handlers, starts HTTP server
internal/models/book.go      # Book, BookInput, ValidationError
internal/store/              # SQLite repository (Open/Create/Get/List/Update/Delete)
internal/handlers/           # HTTP handlers + router
```

## Tests

Unit tests cover the SQLite store (`internal/store`) and integration tests
exercise the full HTTP layer via `httptest` against an in-memory database.

```bash
go test ./...
```

Run with verbose output:

```bash
go test -v ./...
```
