# Book Collection API

A small REST API for managing a book collection, written in Go using only
the standard library `net/http` (Go 1.22+ method+wildcard routing) and
[`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite) — a pure-Go
SQLite driver, so **no CGO is required**.

## Endpoints

| Method | Path           | Description                          |
|--------|----------------|--------------------------------------|
| GET    | `/health`      | Health check → `{"status":"ok"}`     |
| POST   | `/books`       | Create a book (201 on success)       |
| GET    | `/books`       | List all books, supports `?author=`  |
| GET    | `/books/{id}`  | Get a single book (404 if missing)   |
| PUT    | `/books/{id}`  | Update a book (404 if missing)       |
| DELETE | `/books/{id}`  | Delete a book (204, 404 if missing)  |

### Book JSON shape

```json
{
  "id": 1,
  "title": "The Go Programming Language",
  "author": "Alan Donovan",
  "year": 2015,
  "isbn": "9780321774929"
}
```

`title` and `author` are required (whitespace-only values are rejected).
`year` must be in `0..9999`. `isbn` is optional.

## Prerequisites

- Go 1.22 or newer (built and tested on Go 1.26).

## Build & run

```sh
go build -o bookapi ./...
./bookapi              # listens on :8080, uses ./books.db
# or override flags:
./bookapi -addr=:3000 -db=/tmp/books.db
```

## Run directly without building a binary

```sh
go run .
```

## Tests

```sh
go test ./... -v
```

The test suite uses an isolated SQLite database in a per-test temp
directory and covers (via `httptest`):

1. `TestCreateAndGetBook` — POST then GET round-trip and status codes.
2. `TestValidation` — missing/blank `title` and `author` are rejected with 400.
3. `TestListWithAuthorFilter` — listing and `?author=` filtering.
4. `TestUpdateAndDelete` — PUT/DELETE plus 404 paths.
5. `TestHealthCheck` — `/health` returns 200 `{"status":"ok"}`.
6. `TestStoreCRUD` — direct Store/SQLite layer test without HTTP.

## Example session

```sh
curl -s -X POST :8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Test","author":"Me","year":2020,"isbn":"x"}'
curl -s :8080/books
curl -s :8080/books/1
curl -s -X DELETE :8080/books/1 -o /dev/null -w '%{http_code}\n'   # 204
```
