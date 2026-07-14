# Book API

A REST API service for managing a book collection, written in Go using only the
standard library `net/http` (with Go 1.22+ method-based routing) and an embedded
SQLite database (via the pure-Go `modernc.org/sqlite` driver — no CGO required).

## Endpoints

| Method | Path            | Description                          |
|--------|-----------------|--------------------------------------|
| GET    | `/health`       | Health check                         |
| POST   | `/books`        | Create a new book                    |
| GET    | `/books`        | List all books (`?author=` filter)   |
| GET    | `/books/{id}`   | Get a single book by ID              |
| PUT    | `/books/{id}`   | Update a book                        |
| DELETE | `/books/{id}`   | Delete a book                        |

### Book payload

```json
{
  "title":  "The Go Programming Language",
  "author": "Donovan & Kernighan",
  "year":   2015,
  "isbn":   "978-0134190440"
}
```

`title` and `author` are required; `year` and `isbn` are optional.

## Setup

```bash
go mod tidy
```

## Run

```bash
go run .
# listens on :8080, uses ./books.db
```

Flags:

```bash
go run . -addr=:8080 -db=books.db
# Use -db=:memory: for an in-memory database
```

## Examples

```bash
# Create
curl -s localhost:8080/books -d '{"title":"T","author":"A","year":2020}' | jq

# List
curl -s localhost:8080/books | jq

# Filter by author
curl -s 'localhost:8080/books?author=A' | jq

# Update
curl -s -X PUT localhost:8080/books/1 -d '{"title":"T2","author":"A"}' | jq

# Delete
curl -s -X DELETE localhost:8080/books/1 -i
```

## Tests

```bash
go test ./...
```

The suite (`api_test.go`) covers:
1. Create → List → Get → Delete lifecycle plus `?author=` filtering.
2. Input validation (missing `title`/`author`) and bad ID handling.
3. Update (full and missing-resource paths) plus the health check.
