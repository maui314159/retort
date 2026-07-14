# Book Collection REST API

A small REST API service for managing a book collection, written in Go using
the standard library `net/http` router (Go 1.22+ method/path patterns) and
SQLite for storage via the pure-Go driver
[`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite) (no CGO required).

## Endpoints

| Method | Path           | Description                          |
|--------|----------------|--------------------------------------|
| GET    | `/health`      | Health check                         |
| POST   | `/books`       | Create a new book                    |
| GET    | `/books`       | List books (supports `?author=`)     |
| GET    | `/books/{id}`  | Get a single book                    |
| PUT    | `/books/{id}`  | Update a book (partial update)       |
| DELETE | `/books/{id}`  | Delete a book                        |

### Book model

```json
{
  "id": 1,
  "title": "The Go Book",
  "author": "Grace",
  "year": 2020,
  "isbn": "111",
  "created_at": "2026-06-20T12:00:00Z",
  "updated_at": "2026-06-20T12:00:00Z"
}
```

`title` and `author` are required and must be non-empty. `year` must be a
non-negative integer. `isbn` is optional.

## Setup & Run

Requires Go 1.22+.

```bash
# from the project directory
go mod tidy
go run .                  # listens on :8080, uses books.db
go run . -addr :9090 -db /tmp/books.db   # custom flags
```

## Example usage

```bash
# Create
curl -s -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go Book","author":"Grace","year":2020,"isbn":"111"}'

# List all
curl -s localhost:8080/books

# List by author
curl -s 'localhost:8080/books?author=Grace'

# Get one
curl -s localhost:8080/books/1

# Update
curl -s -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go Book (2nd)"}'

# Delete
curl -s -X DELETE localhost:8080/books/1
```

## Tests

```bash
go test ./... -v
```

The test suite includes:

- `TestCreateBookValidation` — input validation (missing/empty title & author, bad year).
- `TestCRUDFlow` — end-to-end create / get / list-filter / update / delete / 404.
- `TestHealthAndNotFound` — health check, missing book, invalid id handling.
- `TestServerIntegration` — real HTTP server round-trip for create.

## Project layout

```
main.go          # entry point, CLI flags, HTTP server
handlers.go      # HTTP handlers and routing
storage.go       # SQLite persistence layer
models.go        # Book model and validation
util.go          # small helpers
handlers_test.go # unit + integration tests
go.mod           # module definition
```
