# Bookstore REST API

A REST API service for managing a book collection, written in Go using
the standard library `net/http` and SQLite for storage.

## Features

| Method | Endpoint        | Description                       |
|--------|-----------------|-----------------------------------|
| GET    | `/health`       | Health check                      |
| POST   | `/books`        | Create a new book                 |
| GET    | `/books`        | List all books (`?author=` filter)|
| GET    | `/books/{id}`   | Get a single book by ID            |
| PUT    | `/books/{id}`   | Update a book                     |
| DELETE | `/books/{id}`   | Delete a book                     |

## Prerequisites

- Go 1.22+ (tested with Go 1.25)

Dependencies are resolved via `go mod` — no manual installation needed.

## Setup & Run

```bash
# from the project directory
go mod tidy
go run .
```

The server listens on `:8080` by default. Override with the `ADDR`
environment variable. The SQLite database file defaults to `books.db`
in the working directory; override with `DB_PATH`.

```bash
ADDR=:9090 DB_PATH=/tmp/books.db go run .
```

## API Usage

### Create a book

```bash
curl -s -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go Programming Language","author":"Alan Donovan","year":2015,"isbn":"978-0134190440"}'
```

Response (201 Created):

```json
{"id":1,"title":"The Go Programming Language","author":"Alan Donovan","year":2015,"isbn":"978-0134190440"}
```

### List books

```bash
curl -s localhost:8080/books
curl -s 'localhost:8080/books?author=Alan%20Donovan'
```

### Get / Update / Delete

```bash
curl -s localhost:8080/books/1
curl -s -X PUT localhost:8080/books/1 -H 'Content-Type: application/json' -d '{"title":"New Title","author":"New Author","year":2020}'
curl -s -X DELETE localhost:8080/books/1
```

## Validation

- `title` and `author` are required (non-empty) for POST and PUT.
- `year`, when provided, must be between 0 and 9999.
- Invalid requests return `400 Bad Request` with a JSON `{"error":"..."}`
  body.

## Tests

```bash
go test -v ./...
```

The test suite uses an in-memory SQLite database and covers:
- Health endpoint
- Create + retrieve a book
- Input validation (missing title / author)
- List with author filter
- Update a book
- Delete a book (and 404 on re-delete)
- 404 for non-existent IDs
- 400 for invalid IDs
- Empty list returns `[]` (not `null`)
