# Books API

A REST API for managing a book collection, written in Go using the standard
library `net/http` and SQLite (`modernc.org/sqlite`, a pure-Go driver — no CGO
required).

## Endpoints

| Method | Path           | Description                          |
|--------|----------------|--------------------------------------|
| GET    | `/health`      | Health check                         |
| POST   | `/books`       | Create a book (title, author, year, isbn) |
| GET    | `/books`       | List books; supports `?author=` filter |
| GET    | `/books/{id}`  | Get a single book                    |
| PUT    | `/books/{id}`  | Update a book                        |
| DELETE | `/books/{id}`  | Delete a book                        |

`title` and `author` are required (validated on create and update).

## Setup

Requires Go 1.22+.

```bash
go mod download
```

## Run

```bash
go run .
```

By default the server listens on `:8080` and stores data in `./books.db`.
Override with flags:

```bash
go run . -addr=:9090 -db=/tmp/books.db
```

## Example

```bash
curl -s -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Go in Action","author":"William Kennedy","year":2015,"isbn":"9781617291784"}'

curl -s 'localhost:8080/books?author=William%20Kennedy'
```

## Test

```bash
go test ./...
```
