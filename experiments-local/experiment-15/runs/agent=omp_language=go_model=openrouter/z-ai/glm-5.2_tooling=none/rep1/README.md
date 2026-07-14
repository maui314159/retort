# bookapi

A small REST API service for managing a book collection, written in Go using
only the standard library (`net/http` with Go 1.22+ method-pattern routing)
and a pure-Go SQLite driver ([`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite),
no CGO required).

## Endpoints

| Method | Path            | Description                          |
|--------|-----------------|--------------------------------------|
| GET    | `/health`       | Health check → `{"status":"ok"}`     |
| POST   | `/books`        | Create a book                        |
| GET    | `/books`        | List all books; supports `?author=`  |
| GET    | `/books/{id}`   | Get a single book                    |
| PUT    | `/books/{id}`   | Update a book                        |
| DELETE | `/books/{id}`   | Delete a book                        |

### Book object

```json
{
  "id": 1,
  "title": "The Pragmatic Programmer",
  "author": "Hunt",
  "year": 1999,
  "isbn": "9780201616224"
}
```

- `title` and `author` are **required** and non-empty.
- `year` must be between 0 and the current year.
- `isbn`, if provided, must be a 10- or 13-digit string.

### Status codes

- `200 OK` — successful GET / PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — invalid JSON, unknown fields, or failed validation
- `404 Not Found` — no book with that ID
- `500 Internal Server Error` — unexpected storage failure

## Setup

Requires Go 1.22+ (built and tested on Go 1.26).

```sh
go build -o bookapi .
./bookapi                       # listens on :8080, stores in books.db
./bookapi -addr :9090 -dsn /tmp/books.db   # custom address / db file
```

## Tests

```sh
go test ./...
```

The suite covers:
- `internal/book` — store-level CRUD, validation rules, author filtering,
  update/delete not-found semantics.
- `internal/server` — HTTP integration tests over `httptest.Server`:
  full create→get→list→filter→update→delete flow, health check, and the
  400/404 error paths (bad JSON, unknown fields, invalid id, missing
  required fields, missing book on update).

## Project layout

```
main.go                      # entry point: flags, graceful shutdown
internal/book/book.go        # Book model + validation
internal/book/store.go       # SQLite-backed store (CRUD)
internal/book/store_test.go  # store unit tests
internal/server/server.go    # HTTP handlers + router
internal/server/server_test.go # HTTP integration tests
```
