# Bookstore API

A REST API service for managing a book collection, written in Go with the
standard library `net/http` and SQLite (via the pure-Go
[`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite) driver — no CGO
required).

## Requirements

- Go 1.22+ (uses method-based routing patterns in `http.ServeMux`)

## Setup

```sh
go mod tidy
```

## Run

```sh
go run .
```

The server listens on `:8080` and stores data in `books.db` in the current
directory. Both are configurable via environment variables:

```sh
ADDR=:9090 DB_PATH=/tmp/mybooks.db go run .
```

Or build a binary:

```sh
go build -o bookstore .
./bookstore
```

## Test

```sh
go test ./...
```

Tests run against isolated in-memory SQLite databases; nothing is written to
disk.

## API

All request and response bodies are JSON. Errors are returned as
`{"error": "<message>"}` with an appropriate status code.

### Health check

```sh
curl http://localhost:8080/health
# 200 {"status":"ok"}
```

### Create a book

`title` and `author` are required (400 otherwise); `year` and `isbn` are
optional.

```sh
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'
# 201 {"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}
```

### List books

```sh
curl http://localhost:8080/books
# 200 [{"id":1,...}, ...]

curl 'http://localhost:8080/books?author=Frank%20Herbert'
# 200 — only books by that author
```

### Get a book by ID

```sh
curl http://localhost:8080/books/1
# 200 {...} — 404 if not found, 400 if the ID is not an integer
```

### Update a book

Full replacement; `title` and `author` are required.

```sh
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune (Revised)","author":"Frank Herbert","year":1966,"isbn":"978-0441172719"}'
# 200 {...} — 404 if not found
```

### Delete a book

```sh
curl -X DELETE http://localhost:8080/books/1
# 204 No Content — 404 if not found
```

## Project layout

| File          | Purpose                                              |
| ------------- | ---------------------------------------------------- |
| `main.go`     | Entry point: config, store setup, HTTP server        |
| `store.go`    | SQLite persistence layer (`Store`, `Book`)           |
| `handlers.go` | HTTP handlers, routing, validation, JSON responses   |
| `main_test.go`| Integration tests using `httptest` + in-memory SQLite |
