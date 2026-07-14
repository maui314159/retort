# BookAPI

A small REST API service for managing a book collection, written in Go and
backed by SQLite.

## Endpoints

| Method   | Path         | Description                          |
|----------|--------------|--------------------------------------|
| `GET`    | `/health`    | Health check                         |
| `POST`   | `/books`     | Create a new book                    |
| `GET`    | `/books`     | List all books (supports `?author=`) |
| `GET`    | `/books/{id}`| Get a single book                    |
| `PUT`    | `/books/{id}`| Update a book                        |
| `DELETE` | `/books/{id}`| Delete a book                        |

### Book shape

```json
{
  "id": 1,
  "title": "The Go Programming Language",
  "author": "Alan A. A. Donovan",
  "year": 2015,
  "isbn": "978-0134190440"
}
```

`title` and `author` are required on create/update. `year` and `isbn` are
optional (default to `0` and `""` respectively).

## Setup

Requires Go 1.21+ (uses `modernc.org/sqlite`, a pure-Go driver — no CGO
needed).

```sh
go mod download
```

## Run

```sh
go run .
```

The server starts on `:8080` and stores data in `./books.db`.

Configuration via environment variables:

| Variable      | Default     | Description               |
|---------------|-------------|---------------------------|
| `BOOKAPI_ADDR`| `:8080`     | Listen address            |
| `BOOKAPI_DB`  | `books.db`  | SQLite database file path  |

## Build

```sh
go build -o bookapi .
./bookapi
```

## Test

```sh
go test ./...
```

## Example usage

```sh
# Create
curl -s localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Go 101","author":"Tapir","year":2019,"isbn":"0001"}' | jq

# List (with author filter)
curl -s 'localhost:8080/books?author=Tapir' | jq

# Get one
curl -s localhost:8080/books/1 | jq

# Update
curl -s -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Go 101 (2nd ed.)","author":"Tapir","year":2021,"isbn":"0001"}' | jq

# Delete
curl -s -X DELETE localhost:8080/books/1 -i
```
