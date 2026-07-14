# Book Collection API

A small REST API for managing a book collection, written in Go using only the
standard library (`net/http`) for routing and [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite)
(a pure-Go, CGO-free SQLite driver) for storage.

## Endpoints

| Method   | Path           | Description                          |
| -------- | -------------- | ------------------------------------ |
| `GET`    | `/health`      | Health check (`{"status":"ok"}`)     |
| `POST`   | `/books`       | Create a new book                    |
| `GET`    | `/books`       | List all books (supports `?author=`) |
| `GET`    | `/books/{id}`  | Get a single book by ID              |
| `PUT`    | `/books/{id}`  | Update a book                        |
| `DELETE` | `/books/{id}`  | Delete a book                        |

### Book object

```json
{
  "id": 1,
  "title": "The Go Programming Language",
  "author": "Donovan & Kernighan",
  "year": 2015,
  "isbn": "978-0134190440"
}
```

`title` and `author` are required (non-empty). `year` and `isbn` are optional.

### Status codes

- `200 OK` — successful GET / PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — invalid JSON, missing required fields, or bad id
- `404 Not Found` — no book with the given id
- `500 Internal Server Error` — unexpected storage failure

## Setup & run

Requirements: Go 1.22+ (built and tested on Go 1.26).

```bash
# from the project directory
go mod download      # fetch the SQLite driver
go run .             # serves on :8080, db at ./books.db
```

Flags:

```bash
go run . -addr=:9090 -db=/tmp/books.db
```

## Examples

```bash
# Create
curl -s localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"TGL","author":"Donovan & Kernighan","year":2015,"isbn":"978-0134190440"}'

# List all
curl -s localhost:8080/books

# Filter by author
curl -s 'localhost:8080/books?author=Alice'

# Get / Update / Delete by id
curl -s localhost:8080/books/1
curl -s -X PUT localhost:8080/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Updated","author":"Alice","year":2020,"isbn":"x"}'
curl -s -X DELETE localhost:8080/books/1
```

## Tests

The test suite spins up an isolated SQLite file per test using `httptest` and
exercises the full HTTP surface end to end.

```bash
go test ./...            # run all tests
go test -race ./...      # with the race detector
go test -v ./...         # verbose
```

## Layout

| File            | Purpose                                              |
| --------------- | ---------------------------------------------------- |
| `main.go`       | Entrypoint: flags, server lifecycle, graceful shutdown |
| `handlers.go`   | HTTP handlers, routing, JSON I/O, validation wiring   |
| `store.go`      | SQLite persistence layer (`Store`)                    |
| `model.go`      | `Book` type and validation                            |
| `main_test.go`  | Integration tests over the real HTTP server           |
