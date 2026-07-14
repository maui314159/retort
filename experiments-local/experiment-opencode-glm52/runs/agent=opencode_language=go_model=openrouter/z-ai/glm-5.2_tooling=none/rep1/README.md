# bookapi

A small REST API service for managing a book collection, written in Go using
only the standard library `net/http` and a pure-Go SQLite driver
(`modernc.org/sqlite`, no CGO required).

## Features

- `POST   /books`       — Create a new book (`title`, `author`, `year`, `isbn`)
- `GET    /books`       — List all books (supports `?author=` filter)
- `GET    /books/{id}`  — Get a single book by ID
- `PUT    /books/{id}`  — Update a book
- `DELETE /books/{id}`  — Delete a book
- `GET    /health`      — Health check

`title` and `author` are required. JSON responses are returned with
appropriate HTTP status codes (`201 Created`, `200 OK`, `204 No Content`,
`400 Bad Request`, `404 Not Found`, `405 Method Not Allowed`).

## Prerequisites

- Go 1.21+ (tested on Go 1.26)

No external system SQLite library is required — the SQLite driver is
pure Go.

## Setup & Run

```sh
# from the project root
go build ./...

# run (defaults to :8080, books.db)
go run .

# or with custom flags
go run . -addr :9090 -db /tmp/books.db
```

## Example Usage

```sh
# create
curl -s -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

# list
curl -s localhost:8080/books

# filter by author
curl -s 'localhost:8080/books?author=Frank%20Herbert'

# get by id
curl -s localhost:8080/books/1

# update
curl -s -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune (Updated)","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

# delete
curl -s -X DELETE localhost:8080/books/1

# health
curl -s localhost:8080/health
```

## Tests

```sh
go test ./... -v
```

The test suite (`handler_test.go`, `storage_test.go`) covers:
- Health check endpoint
- Full create/list/get/update/delete lifecycle, including the `?author=`
  filter and not-found / validation paths
- Invalid JSON handling
- Direct storage-layer CRUD operations
- Model-level input validation invariants

## Project Layout

| File              | Purpose                                            |
|-------------------|----------------------------------------------------|
| `main.go`         | CLI entrypoint, server bootstrap                   |
| `handler.go`      | HTTP handlers and routing                          |
| `storage.go`      | SQLite-backed persistence layer                    |
| `model.go`        | `Book` struct and validation                       |
| `*_test.go`       | Unit + integration tests                           |
