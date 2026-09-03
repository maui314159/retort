# Book Collection REST API

A small REST API service for managing a book collection, written in Go
using only the standard library (`net/http`, `database/sql`) plus
[`github.com/mattn/go-sqlite3`](https://github.com/mattn/go-sqlite3) for
SQLite storage.

## Endpoints

| Method   | Path          | Description                          |
|----------|---------------|--------------------------------------|
| `GET`    | `/health`     | Health check (`{"status":"ok"}`)    |
| `POST`   | `/books`      | Create a new book                    |
| `GET`    | `/books`      | List all books (optional `?author=`) |
| `GET`    | `/books/{id}` | Get a single book                    |
| `PUT`    | `/books/{id}` | Update a book (partial updates ok)   |
| `DELETE` | `/books/{id}` | Delete a book (idempotent)           |

### Book fields

| Field   | Type    | Required on create | Notes                          |
|---------|---------|--------------------|--------------------------------|
| title   | string  | yes (non-empty)    |                                |
| author  | string  | yes (non-empty)    |                                |
| year    | integer | no                 | omitted as `null` if not set   |
| isbn    | string  | no                 |                                |

`id` is assigned by the server and is read-only.

## Setup & Run

Requirements: Go 1.22+ and a C compiler (gcc) for the SQLite driver.

```bash
# from the workspace directory
go mod download          # fetch dependencies
go run .                 # start the server on :8080 using ./books.db
```

Configuration via flags or environment variables:

```bash
go run . -addr=:9090 -db=/tmp/books.db
# or
BOOKAPI_ADDR=:9090 BOOKAPI_DB=/tmp/books.db go run .
```

## Examples

```bash
# Create a book
curl -s -X POST http://localhost:8080/books   -H 'Content-Type: application/json'   -d '{"title":"A Game of Thrones","author":"George R. R. Martin","year":1996,"isbn":"9780553103540"}'

# List books
curl -s http://localhost:8080/books

# Filter by author (case-insensitive exact match)
curl -s 'http://localhost:8080/books?author=alice'

# Get / update / delete
curl -s http://localhost:8080/books/1
curl -s -X PUT http://localhost:8080/books/1 -H 'Content-Type: application/json' -d '{"title":"New Title"}'
curl -s -X DELETE http://localhost:8080/books/1
```

## Status codes

- `200 OK` — successful GET / PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — invalid JSON, invalid id, or failed validation
- `404 Not Found` — book with given id does not exist
- `405 Method Not Allowed` — unsupported HTTP method on a route
- `500 Internal Server Error` — unexpected storage failure

## Tests

```bash
go test ./... -v
```

The test suite uses a temporary SQLite database per test and covers
creation, retrieval, listing/filtering, validation, update, delete,
not-found handling, the health endpoint, and direct Store-layer usage.
