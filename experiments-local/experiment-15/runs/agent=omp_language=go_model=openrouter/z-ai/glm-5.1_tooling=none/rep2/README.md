# Book Collection API

A REST API for managing a book collection, written in Go with SQLite storage.

## Requirements

- Go 1.22+
- GCC (required by `mattn/go-sqlite3` for CGO)

## Setup

```bash
go mod tidy
```

## Run

```bash
go run .
```

The server listens on `:8080` by default. Set the `PORT` environment variable to change it. Set `DB_PATH` to change the SQLite database file (defaults to `books.db`).

## Endpoints

| Method | Path          | Description              |
|--------|---------------|--------------------------|
| GET    | /health       | Health check             |
| POST   | /books        | Create a new book        |
| GET    | /books        | List all books           |
| GET    | /books/{id}   | Get a book by ID         |
| PUT    | /books/{id}   | Update a book            |
| DELETE | /books/{id}   | Delete a book            |

### Query Parameters

- `GET /books?author=<name>` — filter books by author

### Book JSON

```json
{
  "title": "The Go Programming Language",
  "author": "Donovan & Kernighan",
  "year": 2015,
  "isbn": "978-0134190440"
}
```

`title` and `author` are required. `year` and `isbn` are optional.

## Test

```bash
go test ./...
```
