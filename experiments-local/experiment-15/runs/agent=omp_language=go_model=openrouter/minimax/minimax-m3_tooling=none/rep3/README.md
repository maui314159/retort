# bookapi

A small REST API service for managing a book collection. Built in Go
with the standard library's HTTP router (Go 1.22+ pattern matching)
and `modernc.org/sqlite` for embedded persistence.

## Requirements

- Go 1.22 or newer (tested on 1.26)

## Setup

```bash
# Fetch the SQLite driver
go mod tidy

# Build a binary
go build -o bookapi .
```

## Run

```bash
./bookapi
```

The server reads two optional environment variables:

| Variable      | Default      | Meaning                              |
| ------------- | ------------ | ------------------------------------ |
| `BOOKS_ADDR`  | `:8080`      | Listen address (`host:port`)         |
| `BOOKS_DB`    | `./books.db` | SQLite database file (`:memory:` works too) |

Example:

```bash
BOOKS_ADDR=127.0.0.1:9000 BOOKS_DB=/var/lib/bookapi/books.db ./bookapi
```

Send `SIGINT` / `SIGTERM` to shut down gracefully (in-flight requests
are given up to 10 s to finish).

## API

All requests and responses use `application/json`.

### `GET /health`

Liveness probe. Always returns `200 OK`.

```json
{ "status": "ok" }
```

### `POST /books`

Create a book. `title` and `author` are required; `year` and `isbn` are
optional. Returns `201 Created` with the persisted book (including the
newly-assigned `id`).

```bash
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go Programming Language","author":"Alan Donovan","year":2015,"isbn":"978-0134190440"}'
```

Response `201 Created`:

```json
{
  "id": 1,
  "title": "The Go Programming Language",
  "author": "Alan Donovan",
  "year": 2015,
  "isbn": "978-0134190440"
}
```

Validation failures return `400 Bad Request`:

```json
{ "error": "title is required" }
```

### `GET /books`

List all books. Supports an exact-match `?author=` filter. Always
returns a JSON array (never `null`, even when empty).

```bash
curl http://localhost:8080/books
curl 'http://localhost:8080/books?author=Alan%20Donovan'
```

### `GET /books/{id}`

Fetch a single book by ID. Returns `200 OK` on success, `404 Not Found`
if no book has that ID, or `400 Bad Request` for a non-numeric ID.

### `PUT /books/{id}`

Replace the book with the given ID. The request body has the same
shape as `POST`; `title` and `author` are still required. Returns the
updated book, `404` if the ID is unknown, or `400` for validation /
parse errors.

### `DELETE /books/{id}`

Delete a book. Returns `204 No Content` on success, `404 Not Found`
if the ID is unknown, or `400` for a non-numeric ID.

### Status codes summary

| Code | Meaning                                                  |
| ---- | -------------------------------------------------------- |
| 200  | Successful read or update                                |
| 201  | Successful create                                        |
| 204  | Successful delete                                        |
| 400  | Malformed body, unknown field, or missing required field |
| 404  | Book ID not found                                        |
| 405  | Wrong HTTP method for the path                           |
| 500  | Internal server error                                    |

## Project layout

```
.
├── main.go                       # entry point + graceful shutdown
├── go.mod / go.sum
└── internal/books/
    ├── model.go                  # Book struct + validation
    ├── store.go                  # SQLite-backed Store
    ├── handlers.go               # HTTP handlers + routing table
    ├── store_test.go             # store unit tests
    └── handlers_test.go          # handler integration tests
```

## Tests

```bash
go test ./...
go test -race ./...
```

The suite covers:

- CRUD round-trip against an in-memory SQLite database
- `?author=` filter (matching and non-matching authors)
- `ErrNotFound` propagation from `Get` / `Update` / `Delete`
- File-backed persistence (data survives a reopen)
- HTTP happy paths: create, list, get, update, delete
- Validation: missing/empty `title`, missing/empty `author`
- Malformed JSON body
- 404 vs 400 for unknown vs non-numeric IDs
- Empty list result is `[]`, not `null`

## Design notes

- **No third-party HTTP router.** Go 1.22's enhanced `http.ServeMux`
  supports method+path patterns (`GET /books/{id}`) out of the box,
  so the dependency surface stays minimal.
- **Pure-Go SQLite.** `modernc.org/sqlite` ships as a Go module, so
  the binary builds with `CGO_ENABLED=0` and runs anywhere Go does.
- **Single-writer connection pool.** `db.SetMaxOpenConns(1)` avoids
  spurious `database is locked` errors under concurrent traffic;
  swap to a higher value with a WAL-mode migration if the workload
  needs it.
- **Structured errors.** Store errors are mapped to HTTP status codes
  in one place (`writeStoreError`); handlers never need to inspect
  raw error strings.
