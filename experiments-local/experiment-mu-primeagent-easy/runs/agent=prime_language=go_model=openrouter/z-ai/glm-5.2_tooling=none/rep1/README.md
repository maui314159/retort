# Book API

A REST API service for managing a book collection, written in Go using the
standard library `net/http` (1.22+ enhanced routing) and an embedded SQLite
database (`modernc.org/sqlite`, pure Go — no CGO required).

## Features

- `POST /books` — create a new book
- `GET /books` — list all books (supports `?author=` filtering)
- `GET /books/{id}` — retrieve a single book
- `PUT /books/{id}` — update an existing book
- `DELETE /books/{id}` — delete a book
- `GET /health` — health check

All responses are JSON. Input validation enforces that `title` and `author`
are non-empty and rejects unknown JSON fields.

## Requirements

- Go 1.22 or newer

## Setup & run

From the project directory:

```bash
# Download dependencies
go mod download

# Build the binary
go build -o bookapi .

# Run the server (listens on :8080 by default, uses books.db)
./bookapi

# Or run directly
go run .
```

### Configuration

Flags / environment variables:

| Flag   | Env       | Default     | Description                  |
|--------|-----------|-------------|------------------------------|
| `-addr`| `ADDR`    | `:8080`     | address to listen on         |
| `-db`  | `DB_PATH` | `books.db`  | path to the SQLite file      |

Examples:

```bash
# Listen on port 9090 with a custom database file
ADDR=:9090 DB_PATH=./data.db ./bookapi

# Or via flags
go run . -addr :9090 -db ./data.db
```

## API usage

```bash
# Health
curl http://localhost:8080/health

# Create
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go Programming Language","author":"Donovan & Kernighan","year":2015,"isbn":"978-0134190440"}'

# List all
curl http://localhost:8080/books

# List filtered by author
curl 'http://localhost:8080/books?author=Donovan%20%26%20Kernighan'

# Get by id
curl http://localhost:8080/books/1

# Update
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"New Title","author":"New Author","year":2020,"isbn":"x"}'

# Delete
curl -X DELETE http://localhost:8080/books/1
```

### Status codes

| Code | Meaning                          |
|------|----------------------------------|
| 200  | OK (list, get, update)           |
| 201  | Created (create)                 |
| 204  | No Content (delete)             |
| 400  | Bad Request (validation / JSON)  |
| 404  | Not Found                        |
| 500  | Internal Server Error            |

## Tests

```bash
go test -v ./...
```

Tests use an in-memory SQLite database so no files are created on disk.
