# bookapi

A small REST API for managing a book collection, written in Go using only the
standard library and a pure-Go SQLite driver (no CGO required).

## Requirements

- Go **1.22** or newer (the HTTP router uses the new method+path patterns
  introduced in 1.22). Tested with Go 1.26.

## Setup

```sh
# Fetch the SQLite driver and its transitive dependencies
go mod tidy

# (Optional) build a static binary
go build -o bookapi .
```

The SQLite driver (`modernc.org/sqlite`) is pure Go, so no C toolchain is
required.

## Run

```sh
# Defaults: listens on :8080, stores data in ./books.db
./bookapi

# Or via go run
go run .
```

### Environment variables

| Variable       | Default                                                              | Description                                |
| -------------- | -------------------------------------------------------------------- | ------------------------------------------ |
| `ADDR`         | `:8080`                                                              | Address the HTTP server binds to.          |
| `DATABASE_URL` | `file:books.db?_pragma=busy_timeout(5000)&_pragma=journal_mode(WAL)` | SQLite DSN. Use `:memory:` for an in-memory DB. |

The server performs a graceful shutdown on `SIGINT` / `SIGTERM`.

## API

All request and response bodies are JSON. Errors come back as
`{"error": "message"}` with an appropriate HTTP status code.

### `GET /health`

Liveness check. Pings the database; returns `200 {"status":"ok"}` or
`503 {"error":"database unavailable"}`.

### `POST /books`

Create a book. `title` and `author` are required; `year` and `isbn` are
optional.

Request:

```sh
curl -s -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go Programming Language","author":"Alan A. A. Donovan","year":2015,"isbn":"978-0134190440"}'
```

Response: `201 Created` with the new book (id and timestamps populated).

### `GET /books`

List all books. Supports an exact-match `author` filter.

```sh
curl -s http://localhost:8080/books
curl -s 'http://localhost:8080/books?author=Alan%20A.%20A.%20Donovan'
```

Response: `200 OK` with a JSON array (empty array, not `null`, when empty).

### `GET /books/{id}`

Fetch a single book.

```sh
curl -s http://localhost:8080/books/1
```

Response: `200 OK` with the book, or `404 Not Found`.

### `PUT /books/{id}`

Replace a book's fields. `title` and `author` are still required.

```sh
curl -s -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"New Title","author":"New Author","year":2020,"isbn":"..."}'
```

Response: `200 OK` with the updated book (including a refreshed
`updated_at`), or `404 Not Found`.

### `DELETE /books/{id}`

Delete a book.

```sh
curl -s -X DELETE http://localhost:8080/books/1
```

Response: `204 No Content`, or `404 Not Found`.

## Validation

`title` and `author` must be present and non-blank (whitespace-only is
rejected). `year` must be `>= 0` and not more than one year past the current
year. Malformed JSON or a non-numeric `id` in the URL returns `400 Bad Request`.

## Tests

```sh
go test -v ./...
go test -race ./...
```

The test suite uses `httptest.NewServer` and a per-test temporary SQLite file,
so tests are fully isolated and can run in parallel.

## Project layout

```
.
├── main.go             # entry point + graceful shutdown
├── book.go             # Book model
├── store.go            # SQLite storage layer
├── handlers.go         # HTTP handlers + routing
├── handlers_test.go    # unit / integration tests
├── go.mod / go.sum     # module definition
└── README.md
```
