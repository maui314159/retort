# Book Collection API

A small REST API service for managing a book collection, written in Go using
the standard library `net/http` router and SQLite for storage. SQLite access
uses [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite), a pure-Go
driver — no CGO toolchain is required.

## Endpoints

| Method | Path            | Description                          |
|--------|-----------------|--------------------------------------|
| GET    | `/health`       | Health check → `200 {"status":"ok"}`|
| POST   | `/books`        | Create a book (201 on success)       |
| GET    | `/books`        | List books; supports `?author=` filter |
| GET    | `/books/{id}`   | Get a single book (404 if missing)    |
| PUT    | `/books/{id}`   | Update a book (200 / 400 / 404)       |
| DELETE | `/books/{id}`   | Delete a book (204 / 404)             |

### Book JSON shape

```json
{
  "id": 1,
  "title": "Foundation",
  "author": "Isaac Asimov",
  "year": 1951,
  "isbn": "0-553-29335-4",
  "created_at": "2026-06-20T22:21:00Z",
  "updated_at": "2026-06-20T22:21:00Z"
}
```

`title` and `author` are required. Missing either yields `400 {"error":"title and author are required"}`.

## Prerequisites

- Go 1.21+ (built with Go 1.26 here)

No external services are required; SQLite is embedded.

## Setup & run

```sh
# from this directory
go mod download        # fetch the SQLite driver (already in go.sum)

# run with defaults (listens on :8080, uses ./books.db)
go run .

# or override flags
go run . -addr=:3000 -db=/tmp/books.db
```

On first run the `books` table and an `idx_books_author` index are created
automatically.

## Building a binary

```sh
go build -o bookapi .
./bookapi -addr=:8080 -db=books.db
```

## Example usage

```sh
# create
curl -s -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"0441172717"}'

# list all
curl -s localhost:8080/books | jq

# list by author
curl -s 'localhost:8080/books?author=Frank%20Herbert' | jq

# get one (id=1)
curl -s localhost:8080/books/1 | jq

# update
curl -s -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune (Revised)","author":"Frank Herbert","year":1965}' | jq

# delete
curl -i -X DELETE localhost:8080/books/1
```

## Project layout

```
.
├── go.mod            # module bookapi
├── main.go          # entry point: flags + http.ListenAndServe
├── store.go         # Store: SQLite repository + Book model + validation
├── server.go         # HTTP handlers, routing, JSON/errors
└── server_test.go    # integration tests using httptest
```

## Tests

Four integration tests exercise every endpoint and edge case through
`httptest.NewRecorder` against a fresh SQLite file in `t.TempDir()`:

```sh
go test ./... -v
```

- `TestCreateAndGetBook` — create + get + 400 on missing title + 404 on unknown id
- `TestListWithAuthorFilter` — list all, list by `?author=`
- `TestUpdateAndDelete` — PUT (incl. 400), DELETE (204 then 404), created_at preserved
- `TestHealthCheck` — `/health` returns 200 with `status:ok`

Build/vet:

```sh
go build ./...
go vet  ./...
```
