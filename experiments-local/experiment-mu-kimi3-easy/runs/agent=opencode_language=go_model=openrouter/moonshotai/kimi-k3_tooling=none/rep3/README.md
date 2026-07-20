# Book Collection API

A REST API service for managing a book collection, written in Go with the
standard `net/http` router and SQLite (via the pure-Go
[`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite) driver — no CGO
required).

## Requirements

- Go 1.23+ (developed against Go 1.26)

## Setup

```sh
go mod download
```

## Run

```sh
go run .
```

The server listens on `:8080` and stores data in `books.db` in the current
directory. Both are configurable via environment variables:

```sh
PORT=9000 DB_PATH=/tmp/my-books.db go run .
```

Or build a binary:

```sh
go build -o bookapi .
./bookapi
```

## Test

```sh
go test ./...
```

The test suite spins up the full HTTP handler stack against a temporary
SQLite database (via `httptest`), covering health, create + validation,
listing with the author filter, get/update/delete, and 404 handling.

## API

All responses are JSON. Errors have the shape `{"error": "<message>"}`.

| Method | Path          | Description                        | Success status |
|--------|---------------|------------------------------------|----------------|
| GET    | `/health`     | Health check                       | 200            |
| POST   | `/books`      | Create a book                      | 201            |
| GET    | `/books`      | List books (`?author=` to filter)  | 200            |
| GET    | `/books/{id}` | Get a single book                  | 200            |
| PUT    | `/books/{id}` | Update a book (full replacement)   | 200            |
| DELETE | `/books/{id}` | Delete a book                      | 204            |

### Book fields

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "978-0441172719"
}
```

`title` and `author` are required (400 otherwise). `year` and `isbn` are
optional. Unknown IDs return 404; malformed IDs return 400.

### Examples

```sh
# Health check
curl localhost:8080/health

# Create
curl -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'

# List all / filter by author
curl localhost:8080/books
curl 'localhost:8080/books?author=Frank+Herbert'

# Get one
curl localhost:8080/books/1

# Update
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'

# Delete
curl -X DELETE localhost:8080/books/1
```

## Project layout

- `main.go` — entry point, configuration, server startup
- `handlers.go` — HTTP handlers, routing, validation, JSON responses
- `store.go` — SQLite persistence layer
- `handlers_test.go` — integration tests
