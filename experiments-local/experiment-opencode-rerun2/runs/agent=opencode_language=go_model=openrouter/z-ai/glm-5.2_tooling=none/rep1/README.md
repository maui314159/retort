# Book Collection API

A small REST API for managing a book collection, written in Go using the
standard library's `net/http` (Go 1.22+ method-based routing) and SQLite for
persistence via the pure-Go [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite)
driver (no CGO required).

## Endpoints

| Method | Path           | Description                          |
|--------|----------------|--------------------------------------|
| GET    | `/health`      | Health check                         |
| POST   | `/books`       | Create a book                        |
| GET    | `/books`       | List books (supports `?author=` filter) |
| GET    | `/books/{id}`  | Get a single book                    |
| PUT    | `/books/{id}`  | Update a book                        |
| DELETE | `/books/{id}`  | Delete a book                        |

### Book JSON shape

```json
{
  "id": 1,
  "title": "The Go Programming Language",
  "author": "Alan Donovan",
  "year": 2015,
  "isbn": "978-0134190440",
  "created_at": "2026-06-20T22:00:00Z",
  "updated_at": "2026-06-20T22:00:00Z"
}
```

`title` and `author` are required; `year` and `isbn` are optional. Validation
failures return `400 Bad Request` with a `details` array of error messages.

## Setup

Requires Go 1.22+ (tested with Go 1.26).

```bash
# from the project root
go mod tidy
```

## Run

```bash
go run .
# book API listening on :8080 (db=books.db)
```

Flags:

- `-addr` — listen address (default `:8080`)
- `-db` — SQLite database path (default `books.db`); use `file::memory:` for in-memory

### Examples

```bash
# create
curl -s localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Tao of Pooh","author":"Benjamin Hoff","year":1982}'

# list, filtered by author
curl -s 'localhost:8080/books?author=Hoff'

# get
curl -s localhost:8080/books/1

# update
curl -s -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Tao of Pooh","author":"Benjamin Hoff","year":1982}'

# delete
curl -s -X DELETE localhost:8080/books/1
```

## Tests

```bash
go test ./...
```

The suite includes integration tests covering: create + read lifecycle,
input validation, the `?author=` filter, update/delete (including
404 after delete), the health endpoint, and invalid id handling.

## Layout

- `main.go` — entry point, HTTP server, graceful shutdown
- `handlers.go` — HTTP handlers and JSON helpers
- `store.go` — SQLite persistence layer
- `model.go` — `Book` type and input validation
- `errors.go` — sentinel errors
- `api_test.go` — integration tests
