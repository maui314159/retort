# Books API

A REST API service for managing a book collection, written in Go using the
standard library `net/http` (Go 1.22 enhanced routing) and SQLite
(`modernc.org/sqlite`, a pure-Go driver — no CGO required).

## Endpoints

| Method   | Path          | Description                        |
|----------|---------------|------------------------------------|
| `GET`    | `/health`     | Health check                       |
| `POST`   | `/books`      | Create a new book                  |
| `GET`    | `/books`     | List all books (supports `?author=` filter) |
| `GET`    | `/books/{id}` | Get a single book by ID           |
| `PUT`    | `/books/{id}` | Update a book                     |
| `DELETE` | `/books/{id}` | Delete a book                     |

### Book JSON format

```json
{
  "id": 1,
  "title": "The Go Programming Language",
  "author": "Alan Donovan",
  "year": 2015,
  "isbn": "9780134190440"
}
```

`title` and `author` are required. `year` and `isbn` are optional.

## Setup & Run

### Prerequisites

- Go 1.22 or later

### Build and run

```bash
# Download dependencies
go mod download

# Run the server (defaults to :8080, database defaults to books.db)
go run .
```

The server starts on `http://localhost:8080`.

### Configuration (optional environment variables)

| Variable  | Default      | Description                |
|-----------|--------------|----------------------------|
| `ADDR`    | `:8080`      | Listen address             |
| `DB_PATH` | `books.db`   | SQLite database file path  |

Example:

```bash
ADDR=:3000 DB_PATH=/tmp/books.db go run .
```

### Build a binary

```bash
go build -o booksapi .
./booksapi
```

## Tests

```bash
go test ./...
```

Tests use an in-memory SQLite database and the `httptest` package to exercise
the full HTTP stack.

## Example usage

```bash
# Create a book
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go Programming Language","author":"Alan Donovan","year":2015,"isbn":"9780134190440"}'

# List all books
curl http://localhost:8080/books

# Filter by author
curl 'http://localhost:8080/books?author=Alan%20Donovan'

# Get a book by ID
curl http://localhost:8080/books/1

# Update a book
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Updated Title","author":"New Author","year":2024,"isbn":"123"}'

# Delete a book
curl -X DELETE http://localhost:8080/books/1
```
