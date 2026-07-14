# Book Collection API

A REST API for managing a book collection, written in Go using only the
standard library `net/http` (Go 1.22+ method+path routing) and the pure-Go
SQLite driver [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite)
(no CGO required).

## Endpoints

| Method | Path           | Description                          |
|--------|----------------|--------------------------------------|
| GET    | `/health`      | Health check                         |
| POST   | `/books`       | Create a book                        |
| GET    | `/books`       | List all books (`?author=` filter)   |
| GET    | `/books/{id}`  | Get a single book                    |
| PUT    | `/books/{id}`  | Update a book                        |
| DELETE | `/books/{id}`  | Delete a book                        |

### Book JSON shape

```json
{ "id": 1, "title": "...", "author": "...", "year": 2020, "isbn": "..." }
```

`title` and `author` are required on create/update; `year` defaults to `0`
and `isbn` to `""`.

## Setup & Run

```bash
# From the project directory:
go mod tidy        # fetch dependencies
go run .           # starts on :8080 with ./books.db
```

Environment overrides:

- `ADDR`  — listen address (default `:8080`)
- `DB_PATH` — SQLite database file (default `books.db`)

## Examples

```bash
# Create
curl -s localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"The Go Prog. Lang.","author":"Donovan","year":2015,"isbn":"978-013"}'

# List, filtered by author
curl -s 'localhost:8080/books?author=Donovan'

# Get one
curl -s localhost:8080/books/1

# Update
curl -s -X PUT localhost:8080/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Updated","author":"Donovan","year":2020,"isbn":"978-013"}'

# Delete
curl -s -X DELETE localhost:8080/books/1
```

## Tests

```bash
go test ./...
```

The suite (`main_test.go`) covers: create/get/404, input validation for
required fields, list with `?author=` filter, update (incl. 404), delete
(incl. 404), and the health check.
