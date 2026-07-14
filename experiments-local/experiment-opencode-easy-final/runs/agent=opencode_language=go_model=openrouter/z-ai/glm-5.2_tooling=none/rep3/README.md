# bookapi

A small REST API for managing a book collection, written in Go. Books are
stored in an embedded SQLite database (`modernc.org/sqlite`, a pure-Go
driver — no CGO required).

## Endpoints

| Method | Path           | Description                          |
|--------|----------------|--------------------------------------|
| GET    | `/health`      | Liveness check, returns `{"status":"ok"}` |
| POST   | `/books`       | Create a new book                    |
| GET    | `/books`       | List all books; supports `?author=` filter (case-insensitive, exact match) |
| GET    | `/books/{id}`  | Get a single book by ID              |
| PUT    | `/books/{id}`  | Partial update of a book             |
| DELETE | `/books/{id}`  | Delete a book                        |

### Book shape

```json
{
  "id": 1,
  "title": "Refactoring",
  "author": "Martin Fowler",
  "year": 1999,
  "isbn": "0-201-48567-2",
  "created_at": "2026-06-21T08:45:00Z",
  "updated_at": "2026-06-21T08:45:00Z"
}
```

`year` and `isbn` are optional. `title` and `author` are required on create.
On `PUT`, only the supplied fields are merged into the existing record, so
partial updates are supported.

### Status codes

- `200 OK` — successful GET / PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — malformed JSON or invalid `id` path parameter
- `404 Not Found` — book with given `id` does not exist
- `422 Unprocessable Entity` — input failed validation; the body contains
  `{ "error": "validation failed", "fields": { "<field>": "<reason>" } }`
- `500 Internal Server Error` — unexpected database failure

## Setup

Requires Go 1.26+.

```bash
# fetch dependencies
go mod tidy

# build
go build -o bookapi ./...

# run (defaults to :8080, ./books.db)
./bookapi

# custom address / db path
./bookapi -addr :9000 -db /tmp/books.db
```

## Running the tests

```bash
go test -v ./...
```

The suite includes:

- `TestBookInputValidation` — table-driven unit test for create-time input
  validation (required-field checks, year range, ISBN length).
- `TestBookInputPartialValidation` — table-driven unit test for update-time
  partial validation.
- `TestStoreCreateGetDelete` — DB-layer CRUD round-trip.
- `TestStoreListAuthorFilter` — DB-layer listing with the `?author=` filter.
- `TestStoreUpdateMerge` — DB-layer partial update semantics.
- `TestIntegrationFullLifecycle` — end-to-end create → get → list → update →
  delete through the real HTTP router against an isolated SQLite file.
- `TestIntegrationValidationAndHealth` — `/health`, validation error
  responses, malformed JSON, invalid id, missing-book lookup.
- `TestIntegrationRouteOrder` — verifies the `?author=` query route takes
  precedence over the plain `/books` route.

## Project layout

```
.
├── go.mod         # module + dependencies
├── main.go        # entrypoint: flags, server, graceful shutdown
├── models.go      # Book type, request payload, validation
├── db.go          # Store: SQLite schema + CRUD queries
├── handlers.go    # HTTP handlers and router
└── main_test.go   # unit + integration tests
```

## Example session

```bash
# create
curl -s -X POST :8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Clean Code","author":"Robert C. Martin","year":2008,"isbn":"978-0-13-235088-4"}'

# list
curl -s :8080/books

# list filtered by author
curl -s ':8080/books?author=Robert%20C.%20Martin'

# get one (replace 1 with a real id)
curl -s :8080/books/1

# partial update
curl -s -X PUT :8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year":2022}'

# delete
curl -s -X DELETE :8080/books/1 -o /dev/null -w '%{http_code}\n'  # -> 204
```
