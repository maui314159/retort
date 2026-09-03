# Books API

A small REST API for managing a book collection, written in Go using only the
standard library (`net/http`) and SQLite via the pure-Go `modernc.org/sqlite`
driver (no CGO required).

## Endpoints

| Method | Path            | Description                          |
|--------|-----------------|--------------------------------------|
| GET    | `/health`       | Health check                         |
| POST   | `/books`        | Create a book (`title`, `author`, `year`, `isbn`) |
| GET    | `/books`        | List books (optional `?author=` filter) |
| GET    | `/books/{id}`   | Get a single book                    |
| PUT    | `/books/{id}`   | Update a book                        |
| DELETE | `/books/{id}`   | Delete a book                        |

`title` and `author` are required (validated on create and update). JSON is
returned for all responses with appropriate HTTP status codes
(`201 Created`, `400 Bad Request`, `404 Not Found`, `204 No Content`, etc.).

## Setup & Run

Requires Go 1.22+.

```bash
# from the project directory
go mod tidy
go run .
```

The server listens on `:8080` by default and writes to `books.db` in the
working directory. Override with flags:

```bash
go run . -addr=:9090 -db=/tmp/books.db
```

## Examples

```bash
# Create
curl -s localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Herbert","year":1965,"isbn":"XYZ"}'

# List (optionally filtered by author)
curl -s 'localhost:8080/books?author=Herbert'

# Get
curl -s localhost:8080/books/1

# Update
curl -s -X PUT localhost:8080/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune Revised","author":"Herbert","year":1980,"isbn":"XYZ"}'

# Delete
curl -s -X DELETE localhost:8080/books/1
```

## Tests

```bash
go test ./...
```

Tests use an in-memory SQLite database (`:memory:`) and cover the full
create/get/list/delete lifecycle, input validation, author filtering, and
not-found handling.
