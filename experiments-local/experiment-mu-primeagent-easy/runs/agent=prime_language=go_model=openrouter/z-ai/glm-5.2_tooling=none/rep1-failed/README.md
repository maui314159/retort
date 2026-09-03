# Book Collection REST API

A small REST API service for managing a book collection, written in Go.
It uses the standard library `net/http` router (Go 1.22+ enhanced `ServeMux`)
and stores data in an embedded **SQLite** database via the pure-Go
[`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite) driver (no CGO
required).

## Features

- `POST /books` — create a new book (`title`, `author`, `year`, `isbn`).
- `GET /books` — list all books; supports an optional `?author=<name>` filter.
- `GET /books/{id}` — get a single book by ID.
- `PUT /books/{id}` — update an existing book.
- `DELETE /books/{id}` — delete a book.
- `GET /health` — health check.

All responses are JSON. Input validation enforces that `title` and `author`
are required (missing fields return `400 Bad Request`); a non-existent book ID
returns `404 Not Found`.

## Prerequisites

- Go 1.22 or newer.

The SQLite driver is pure Go, so no system-level SQLite library is needed.

## Setup & Run

From the workspace directory:

```bash
# Download dependencies
go mod tidy

# Build the binary
go build -o bookapi ./...

# Run the server (defaults to :8080, uses ./books.db)
./bookapi
```

Environment variables:

| Variable  | Default    | Description                          |
|-----------|-----------|--------------------------------------|
| `ADDR`    | `:8080`   | Address the HTTP server listens on. |
| `DB_PATH` | `books.db`| Path to the SQLite database file.   |

## Tests

```bash
go test ./...
```

Tests use an in-memory SQLite database, so they do not touch the on-disk
`books.db` file.

## Example Usage

```bash
# Create a book
curl -X POST http://localhost:8080/books   -H 'Content-Type: application/json'   -d '{"title":"The Go Programming Language","author":"Alan Donovan","year":2015,"isbn":"978-0134190440"}'

# List all books
curl http://localhost:8080/books

# List books by a specific author
curl 'http://localhost:8080/books?author=Alan%20Donovan'

# Get a single book (id 1)
curl http://localhost:8080/books/1

# Update a book
curl -X PUT http://localhost:8080/books/1   -H 'Content-Type: application/json'   -d '{"title":"Updated Title","author":"Alan Donovan","year":2016,"isbn":"978-0134190440"}'

# Delete a book
curl -X DELETE http://localhost:8080/books/1

# Health check
curl http://localhost:8080/health
```

## Project Layout

```
.
├── go.mod
├── main.go            # entrypoint: wires up the store, handler and HTTP server
├── model/
│   └── book.go        # Book and BookInput types + validation
├── store/
│   └── book.go        # SQLite-backed CRUD operations
└── handler/
    ├── book.go        # HTTP handlers
    └── book_test.go   # unit/integration tests
```
