# Book Collection API

A small REST API service for managing a book collection, written in Go using
only the standard library (`net/http` with Go 1.22+ method/path routing) and
SQLite via the pure-Go driver `modernc.org/sqlite` (no CGO required).

## Features

- `POST   /books`        — create a book (`title`, `author`, `year`, `isbn`)
- `GET    /books`        — list books, optional `?author=` filter
- `GET    /books/{id}`   — get a single book
- `PUT    /books/{id}`   — update a book
- `DELETE /books/{id}`   — delete a book
- `GET    /health`       — health check

`title` and `author` are required (non-empty after trimming). `year` must be
between `0` and `9999`. Responses are JSON with appropriate HTTP status codes:

| Outcome              | Status             |
|----------------------|--------------------|
| Successful create    | `201 Created`      |
| Successful get/list  | `200 OK`           |
| Successful update    | `200 OK`           |
| Successful delete    | `204 No Content`   |
| Validation error     | `400 Bad Request`  |
| Unknown id           | `404 Not Found`    |
| Server error         | `500 Internal ...` |

## Requirements

- Go 1.22 or newer (tested with Go 1.26)

## Setup & Run

```bash
# from the project directory
go mod download
go run .            # listens on :8080, uses ./books.db
```

Flags:

```bash
go run . -addr=:9090 -db=/tmp/books.db
```

## Examples

```bash
# Create
curl -s -X POST localhost:8080/books \
  -H 'content-type: application/json' \
  -d '{"title":"The Go Book","author":"Donovan","year":2015,"isbn":"9780134190440"}'

# List
curl -s localhost:8080/books

# Filter by author
curl -s 'localhost:8080/books?author=Donovan'

# Get one
curl -s localhost:8080/books/1

# Update
curl -s -X PUT localhost:8080/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"New Title","author":"Donovan","year":2016,"isbn":"9780134190440"}'

# Delete
curl -i -X DELETE localhost:8080/books/1

# Health
curl -s localhost:8080/health
```

## Tests

```bash
go test ./...
go test -v ./...
```

Tests cover:

- `store_test.go` — SQLite store CRUD lifecycle, list filtering,
  and `ErrNotFound` semantics for missing records.
- `server_test.go` — HTTP integration tests via `httptest`:
  health endpoint, input validation error cases, full
  create/get/list/update/delete lifecycle including 404 and 400 paths,
  and a method-not-allowed / unmatched route case.

## Project Layout

```
main.go        # entrypoint, flags, http.ListenAndServe
store.go       # Book type, Store interface, SQLiteStore implementation
server.go      # HTTP handlers, routing, validation, JSON helpers
*_test.go      # unit + integration tests
```
