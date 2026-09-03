# Book Collection API

A REST API service for managing a book collection, written in Go using the
standard library `net/http` (Go 1.22 enhanced routing) and an embedded
SQLite database (`modernc.org/sqlite`, pure Go — no CGO required).

## Features

| Method   | Endpoint        | Description                         |
| -------- | --------------- | ----------------------------------- |
| `GET`    | `/health`       | Health check                        |
| `POST`   | `/books`        | Create a new book                   |
| `GET`    | `/books`        | List all books (`?author=` filter)  |
| `GET`    | `/books/{id}`  | Get a single book by ID             |
| `PUT`    | `/books/{id}`  | Update a book                       |
| `DELETE` | `/books/{id}`  | Delete a book                       |

A book has four fields: `title` (required), `author` (required), `year`,
and `isbn`.

## Prerequisites

- Go 1.22+

## Setup & Run

```bash
# from the project root
go mod tidy          # download dependencies

# run the server (listens on :8080 by default, stores in books.db)
go run .
```

### Configuration via environment variables

| Variable   | Default     | Description                       |
| ---------- | ----------- | --------------------------------- |
| `ADDR`     | `:8080`     | Listen address                    |
| `DB_PATH`  | `books.db`  | SQLite database file path         |

Example:

```bash
ADDR=:3000 DB_PATH=/tmp/books.db go run .
```

### Build the binary

```bash
go build -o bookapi .
./bookapi
```

## API Examples

### Health check

```bash
curl http://localhost:8080/health
# {"status":"ok"}
```

### Create a book

```bash
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Clean Code","author":"Robert Martin","year":2008,"isbn":"9780132350884"}'
```

Response — `201 Created`:

```json
{"id":1,"title":"Clean Code","author":"Robert Martin","year":2008,"isbn":"9780132350884"}
```

### List books (with optional author filter)

```bash
curl http://localhost:8080/books
curl 'http://localhost:8080/books?author=Robert%20Martin'
```

### Get, update, delete a book

```bash
curl http://localhost:8080/books/1
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Clean Code (2nd)","author":"Robert Martin","year":2021,"isbn":"9780132350884"}'
curl -X DELETE http://localhost:8080/books/1
```

## Input Validation

- `title` and `author` are required. A request missing either field
  returns `400 Bad Request` with a JSON `{"error":"..."}` body.
- A non-existent or invalid book ID returns `404 Not Found`.
- Malformed JSON returns `400 Bad Request`.

## Tests

The project includes store-level unit tests and HTTP handler integration
tests (10 test functions, 13 sub-tests total):

```bash
go test -v ./...
```

Test coverage:

- `TestStoreCreateGet` — store create + retrieve
- `TestStoreGetAllFilter` — store listing with author filter
- `TestStoreUpdateDelete` — store update + delete
- `TestHTTPHealth` — health endpoint
- `TestHTTPCreateAndGet` — HTTP create + get by ID
- `TestHTTPValidation` — missing title/author returns 400
- `TestHTTPListWithAuthorFilter` — HTTP list + `?author=` filter
- `TestHTTPUpdate` — HTTP PUT update
- `TestHTTPDelete` — HTTP delete + subsequent 404
- `TestHTTPNotFound` — missing book returns 404
- `TestHTTPInvalidJSON` — malformed body returns 400

## Project Layout

```
.
├── go.mod           # module definition
├── go.sum           # dependency checksums
├── main.go          # entry point and server bootstrap
├── models.go        # Book and request types + validation
├── store.go         # SQLite-backed Store implementation
├── handler.go       # HTTP handlers and routing
└── handler_test.go  # unit and integration tests
```
