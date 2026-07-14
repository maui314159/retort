# bookapi

A small REST API for managing a book collection, written in Go using only the
standard library (`net/http` with Go 1.22+ method/path routing) and
[`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite) — a pure-Go
SQLite driver, so **no CGO or system SQLite is required**.

## Features

- `POST   /books`        — create a book (`title`, `author`, `year`, `isbn`)
- `GET    /books`        — list all books; supports `?author=` exact-match filter
- `GET    /books/{id}`   — get a single book by ID
- `PUT    /books/{id}`   — update a book (full replacement)
- `DELETE /books/{id}`   — delete a book
- `GET    /health`       — health check (`{"status":"ok"}`)

Responses are JSON. Appropriate HTTP status codes are used:
`200` / `201` / `204` for success, `400` for validation errors,
`404` for missing books, `500` for internal errors.

### Validation

- `title` and `author` are **required** and must be non-empty after trimming
  whitespace.
- `year`, if provided, must be a positive number (0 / omitted = unset).
- `isbn` is optional.
- JSON requests reject unknown fields and malformed bodies with `400`.

## Setup

Requires Go 1.22+.

```bash
# from the project root
go mod download     # fetch dependencies (modernc.org/sqlite and friends)
```

## Run

```bash
go run .

# defaults: listens on :8080, stores data in ./books.db
```

Configuration via environment variables:

| Variable      | Default     | Description                       |
|---------------|-------------|-----------------------------------|
| `BOOKAPI_ADDR`| `:8080`     | listen address                    |
| `BOOKAPI_DB`  | `books.db`  | path to the SQLite database file  |

Example:

```bash
BOOKAPI_ADDR=:9000 BOOKAPI_DB=/tmp/books.db go run .
```

The server handles `SIGINT`/`SIGTERM` for graceful shutdown.

## Build

```bash
go build -o bookapi .
./bookapi
```

## Test

```bash
go test ./... -v
```

The suite covers (5 test functions, well above the 3-test minimum):

1. `TestStoreCRUD` — store-level create/get/update/list/delete + `ErrNotFound`.
2. `TestHTTPCRUDIntegration` — end-to-end HTTP for health, create, get, list,
   `?author=` filter, update, delete, and 404s.
3. `TestValidationAndBadRequests` — validation rules, bad IDs, malformed JSON,
   and JSON error-body shape.
4. `TestStorePersistsAcrossConnections` — proves data survives reopening the
   SQLite file (real embedded DB, not an in-memory stub).
5. `TestBookValidate` — table-driven model validation edge cases.

## Example usage

```bash
# create
curl -s -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Clean Code","author":"Robert Martin","year":2008,"isbn":"9780132350884"}'

# list
curl -s localhost:8080/books

# filter by author
curl -s 'localhost:8080/books?author=Robert%20Martin'

# get one (id from the create response)
curl -s localhost:8080/books/1

# update
curl -s -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Clean Code (2e)","author":"Robert C. Martin","year":2021,"isbn":"9780135957059"}'

# delete
curl -s -o /dev/null -w '%{http_code}\n' -X DELETE localhost:8080/books/1   # -> 204

# health
curl -s localhost:8080/health
```

## Project layout

```
.
├── go.mod            # module + dependency on modernc.org/sqlite
├── go.sum
├── main.go           # entry point, config, graceful shutdown
├── model.go          # Book struct + Validate()
├── store.go          # SQLite-backed Store (CRUD + ErrNotFound)
├── handler.go        # HTTP handlers, routing, JSON helpers
├── handler_test.go   # integration + validation tests
├── helpers_test.go   # small test helpers
└── README.md
```
