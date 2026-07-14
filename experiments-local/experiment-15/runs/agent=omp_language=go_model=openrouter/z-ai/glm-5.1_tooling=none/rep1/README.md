# Book Collection API

A REST API for managing a book collection, backed by SQLite.

## Setup

Requires Go 1.22+ (uses enhanced `ServeMux` routing with method patterns).

```sh
go build -o bookapi .
```

## Run

```sh
./bookapi
```

Listens on `:8080` by default. Configure with environment variables:

| Variable  | Default     | Description            |
|-----------|-------------|------------------------|
| `ADDR`    | `:8080`     | Listen address         |
| `DB_PATH` | `books.db`  | SQLite database file   |

## Endpoints

| Method | Path          | Description               |
|--------|---------------|---------------------------|
| GET    | /health       | Health check              |
| POST   | /books        | Create a book             |
| GET    | /books        | List books (?author=...)  |
| GET    | /books/{id}   | Get a book by ID          |
| PUT    | /books/{id}   | Update a book             |
| DELETE | /books/{id}   | Delete a book             |

### Book fields

| Field  | Type   | Required | Notes            |
|--------|--------|----------|------------------|
| title  | string | yes      |                  |
| author | string | yes      |                  |
| year   | int    | no       |                  |
| isbn   | string | no       |                  |

### Example

```sh
# Create
curl -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go Programming Language","author":"Donovan & Kernighan","year":2015,"isbn":"978-0134190440"}'

# List all
curl localhost:8080/books

# Filter by author
curl 'localhost:8080/books?author=Donovan%20%26%20Kernighan'

# Get one
curl localhost:8080/books/1

# Update
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Updated Title","author":"New Author","year":2024}'

# Delete
curl -X DELETE localhost:8080/books/1
```

## Test

```sh
go test -v ./...
```
