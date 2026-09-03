# Books API

A small REST API for managing a book collection, written in Go using only the
standard library `net/http` and a pure-Go SQLite driver
([`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite), no CGO
required).

## Endpoints

| Method   | Path           | Description                          |
|----------|----------------|--------------------------------------|
| `GET`    | `/health`      | Health check                         |
| `POST`   | `/books`       | Create a new book                    |
| `GET`    | `/books`       | List all books (supports `?author=`) |
| `GET`    | `/books/{id}`  | Get a single book                    |
| `PUT`    | `/books/{id}`  | Update a book                        |
| `DELETE` | `/books/{id}`  | Delete a book                        |

### Book shape

```json
{
  "id": 1,
  "title": "The Go Programming Language",
  "author": "Alan Donovan",
  "year": 2015,
  "isbn": "978-0134190440"
}
```

`title` and `author` are required; requests missing them are rejected with
`400 Bad Request`.

## Setup & run

Requirements: Go 1.22+.

```bash
# from the workspace directory
go mod download
go run .
```

The server starts on `http://localhost:8080` and stores data in `books.db`
(SQLite) in the working directory.

### Example

```bash
# create
curl -s -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go","author":"A. Author","year":2020,"isbn":"111"}'

# list
curl -s localhost:8080/books

# filter by author
curl -s 'localhost:8080/books?author=A.%20Author'

# get one
curl -s localhost:8080/books/1

# update
curl -s -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go 2","author":"A. Author","year":2021,"isbn":"111"}'

# delete
curl -s -X DELETE localhost:8080/books/1
```

## Tests

```bash
go test ./...
```

The test suite (`main_test.go`) covers: create + get, input validation, list
with author filter, update + delete lifecycle, and the health check, all
against an in-memory SQLite database.
