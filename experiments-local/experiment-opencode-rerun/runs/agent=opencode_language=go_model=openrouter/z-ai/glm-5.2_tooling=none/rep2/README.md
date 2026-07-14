# bookapi

A small REST API service for managing a book collection, written in Go using
only the standard library for HTTP routing (Go 1.22+ method-pattern `ServeMux`)
and `modernc.org/sqlite` (a pure-Go SQLite driver — no CGO required) for
storage.

## Endpoints

| Method | Path               | Description                                  |
|--------|--------------------|----------------------------------------------|
| GET    | `/health`          | Health check → `{"status":"ok"}` (200)       |
| POST   | `/books`           | Create a book (201 on success, 400 on invalid input) |
| GET    | `/books`           | List all books; supports `?author=` filter (case-insensitive contains) |
| GET    | `/books/{id}`     | Get one book (200, or 404 if not found, 400 on bad id) |
| PUT    | `/books/{id}`      | Replace a book (200, 404, 400) |
| DELETE | `/books/{id}`      | Delete a book (204, 404, 400 on bad id) |

### Book schema

```json
{
  "id": 1,
  "title": "The Go Approach",
  "author": "A. Linguist",
  "year": 2023,
  "isbn": "111-222",
  "created_at": "2026-06-20T22:00:00Z",
  "updated_at": "2026-06-20T22:00:00Z"
}
```

### Validation rules

- `title` and `author` are **required** (non-empty after trimming).
- `year` must be in `[0, 9999]`.
- Length caps: `title` ≤ 1024, `author` ≤ 512, `isbn` ≤ 32.
- Request bodies must be valid JSON; unknown fields are rejected.

## Setup & run

```bash
# From the project directory:
go mod tidy          # fetch the SQLite driver
go run .             # starts on :8080 with books.db in the cwd

# Override via flags or env:
go run . --addr=:9090 --db=/tmp/books.db
BOOKAPI_ADDR=:9090 BOOKAPI_DB=/tmp/books.db go run .
```

Build a binary:

```bash
go build -o bookapi .
./bookapi
```

## Quick smoke test

```bash
curl -s localhost:8080/health
curl -s -X POST localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"The Go Approach","author":"A. Linguist","year":2023,"isbn":"111"}'
curl -s 'localhost:8080/books?author=Linguist'
curl -s -X DELETE localhost:8080/books/1 -i
```

## Tests

```bash
go test ./... -v
go test -cover ./...
```

The suite in `main_test.go` includes four test functions covering:

1. `TestCreateGetUpdateDeleteFlow` — full CRUD lifecycle + post-delete 404.
2. `TestValidationRejectsMissingFields` — required-field enforcement at POST and PUT.
3. `TestListAndAuthorFilter` — list, health, and `?author=` filter behavior.
4. `TestInvalidIDAndUnknownFields` — path-id validation, 404 for unknown ids, strict JSON decoding (unknown fields, empty body).

Each test uses an isolated SQLite file under `t.TempDir()` and an
`httptest.NewServer`, so tests run in parallel safely and leave no artifacts.

## Layout

```
bookapi/
├── go.mod
├── main.go         # entrypoint, flags, server wiring
├── handlers.go    # HTTP handlers, JSON I/O, error responses
├── models.go      # Book struct, validation, DB schema, openDB
├── store.go       # SQL CRUD helpers (create/list/get/update/delete)
└── main_test.go   # integration tests via httptest
```
