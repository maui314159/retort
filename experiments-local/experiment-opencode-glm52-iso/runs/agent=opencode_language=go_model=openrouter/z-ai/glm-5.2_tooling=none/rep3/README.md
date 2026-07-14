# Book Collection API

A REST API service for managing a book collection, written in Go using only the
standard library `net/http` and an embedded SQLite database
([modernc.org/sqlite](https://pkg.go.dev/modernc.org/sqlite), a pure-Go driver
— no CGO required).

## Endpoints

| Method   | Path         | Description                          |
| -------- | ------------ | ------------------------------------ |
| `GET`    | `/health`    | Health check                         |
| `POST`   | `/books`     | Create a new book                    |
| `GET`    | `/books`     | List all books (supports `?author=`) |
| `GET`    | `/books/{id}`| Get a single book by ID              |
| `PUT`    | `/books/{id}`| Update a book                        |
| `DELETE` | `/books/{id}`| Delete a book                        |

### Book shape

```json
{
  "id": 1,
  "title": "The Go Book",
  "author": "A. Author",
  "year": 2020,
  "isbn": "1234567890"
}
```

`title` and `author` are required; `year` defaults to `0` and `isbn` defaults
to `""` if omitted.

## Setup

Requires Go 1.21+ (no external services — SQLite is embedded).

```bash
# install dependencies
go mod download

# run the server (listens on :8080, uses ./books.db)
go run .
```

## Usage examples

```bash
# health
curl http://localhost:8080/health

# create
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go Book","author":"A. Author","year":2020,"isbn":"1234567890"}'

# list all
curl http://localhost:8080/books

# list with author filter
curl 'http://localhost:8080/books?author=A.%20Author'

# get one
curl http://localhost:8080/books/1

# update
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"New Title","author":"A. Author","year":2021,"isbn":"x"}'

# delete
curl -X DELETE http://localhost:8080/books/1
```

## Tests

```bash
go test ./...
```

The test suite (`main_test.go`) is an in-memory integration test covering:

- create + get a book
- input validation (missing title / author)
- list with `?author=` filter
- update + delete lifecycle
- health check
