# Book Collection API

A REST API service for managing a book collection, written in Go with the
standard library (`net/http`) and SQLite (via the pure-Go
[`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite) driver — no cgo
required).

## Requirements

- Go 1.22+ (developed/tested with Go 1.26)

## Setup

```sh
go mod download
go build -o bookapi .
```

## Run

```sh
./bookapi
```

Configuration via environment variables:

| Variable  | Default    | Description                  |
|-----------|------------|------------------------------|
| `ADDR`    | `:8080`    | Listen address               |
| `DB_PATH` | `books.db` | SQLite file (`:memory:` for ephemeral) |

## API

| Method   | Path           | Description                                  |
|----------|----------------|----------------------------------------------|
| `GET`    | `/health`      | Health check → `200 {"status":"ok"}`         |
| `POST`   | `/books`       | Create a book → `201` (`400` on bad input)   |
| `GET`    | `/books`       | List all books; `?author=X` filters by author |
| `GET`    | `/books/{id}`  | Get one book → `200` / `404` / `400`         |
| `PUT`    | `/books/{id}`  | Update a book → `200` / `404` / `400`        |
| `DELETE` | `/books/{id}`  | Delete a book → `204` / `404`                |

Book JSON fields: `title` (required), `author` (required), `year`, `isbn`.
Responses are JSON; errors are `{"error": "..."}`.

### Examples

```sh
# Create
curl -s -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Left Hand of Darkness","author":"Ursula Le Guin","year":1969,"isbn":"978-0441478125"}'

# List (all / filtered)
curl -s localhost:8080/books
curl -s 'localhost:8080/books?author=Ursula+Le+Guin'

# Get / update / delete
curl -s localhost:8080/books/1
curl -s -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Left Hand of Darkness","author":"Ursula K. Le Guin","year":1969,"isbn":"978-0441478125"}'
curl -s -o /dev/null -w '%{http_code}\n' -X DELETE localhost:8080/books/1
```

## Tests

```sh
go test ./...
```

Integration tests spin up the real HTTP server (`httptest`) backed by an
in-memory SQLite database, covering health, CRUD, validation, the author
filter, and 404/400 paths.
