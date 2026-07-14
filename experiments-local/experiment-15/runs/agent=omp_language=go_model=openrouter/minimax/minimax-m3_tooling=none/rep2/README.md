# Books API

A small REST API for managing a book collection, written in Go with an
embedded SQLite store.

## Endpoints

| Method | Path             | Description                                   |
| ------ | ---------------- | --------------------------------------------- |
| GET    | `/health`        | Liveness probe. Returns `{"status":"ok"}`.    |
| POST   | `/books`         | Create a book.                                |
| GET    | `/books`         | List books. Optional `?author=` filter.       |
| GET    | `/books/{id}`    | Fetch one book.                               |
| PUT    | `/books/{id}`    | Replace a book's fields.                      |
| DELETE | `/books/{id}`    | Delete a book.                                |

### Book shape

```json
{
  "id": 1,
  "title": "Refactoring",
  "author": "Martin Fowler",
  "year": 1999,
  "isbn": "0201485672"
}
```

- `id` is assigned by the server and ignored on create/update.
- `title` and `author` are required (after trimming whitespace).
- `year` must be non-negative; `0` is allowed when unknown.
- `isbn` is optional.

### Status codes

| Code | Meaning                                            |
| ---- | -------------------------------------------------- |
| 200  | Successful read or update.                         |
| 201  | Book created.                                      |
| 204  | Book deleted (no body).                            |
| 400  | Validation error (missing field, bad JSON, bad ID).|
| 404  | Book does not exist.                               |
| 405  | Method not allowed for the path.                   |
| 500  | Server error.                                      |

Error responses are JSON: `{"error": "<message>"}`.

## Running

The server is a single static binary. The database path and listen address
are configurable via environment variables.

```bash
# default: listens on :8080, persists to ./books.db
go run .

# override either
BOOKS_ADDR=127.0.0.1:9000 BOOKS_DB=/var/lib/books.db go run .
```

Or build a binary:

```bash
go build -o books .
./books
```

### Configuration

| Variable     | Default     | Description                              |
| ------------ | ----------- | ---------------------------------------- |
| `BOOKS_ADDR` | `:8080`     | `host:port` for the HTTP listener.       |
| `BOOKS_DB`   | `books.db`  | Path to the SQLite database file.        |

The server uses `modernc.org/sqlite`, a pure-Go SQLite driver, so no C
toolchain is required.

## Examples

```bash
# Create
curl -s -X POST http://localhost:8080/books \
     -H 'Content-Type: application/json' \
     -d '{"title":"Refactoring","author":"Martin Fowler","year":1999,"isbn":"0201485672"}'

# List with filter
curl -s 'http://localhost:8080/books?author=fowler'

# Get one
curl -s http://localhost:8080/books/1

# Update
curl -s -X PUT http://localhost:8080/books/1 \
     -H 'Content-Type: application/json' \
     -d '{"title":"Refactoring 2e","author":"Martin Fowler","year":2018}'

# Delete
curl -s -X DELETE -o /dev/null -w '%{http_code}\n' http://localhost:8080/books/1
```

## Project layout

```
.
├── main.go                  # entry point: flags, server lifecycle
├── internal/
│   ├── book/                # Book domain type + Input validation
│   │   └── book.go
│   ├── store/               # SQLite-backed persistence
│   │   ├── store.go
│   │   └── store_test.go
│   └── api/                 # HTTP handlers + routing
│       ├── api.go
│       └── api_test.go
├── go.mod
├── go.sum
└── README.md
```

The packages are layered: `book` is a pure value type with no I/O,
`store` is the only place that knows SQL, and `api` is the only place
that knows HTTP. The wiring lives in `main.go`.

## Testing

```bash
go test ./...
```

There are 22 tests covering the store layer (CRUD, not-found, filter
semantics) and the API layer (every endpoint, validation, error mapping,
method-not-allowed, unknown route). All tests use a fresh SQLite file
under `t.TempDir()` so they can run in parallel without interfering.
