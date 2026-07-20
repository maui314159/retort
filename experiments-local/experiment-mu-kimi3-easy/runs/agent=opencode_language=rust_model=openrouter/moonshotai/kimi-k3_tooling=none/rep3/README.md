# book-api

A REST API service for managing a book collection, written in Rust with
[axum](https://docs.rs/axum) and SQLite (via
[rusqlite](https://docs.rs/rusqlite), bundled — no system SQLite required).

## Requirements

- Rust toolchain (stable, 1.75+): https://rustup.rs

## Setup

```sh
cargo build
```

## Run

```sh
cargo run
```

The server listens on `http://0.0.0.0:3000` by default and stores data in
`books.db` in the current directory. Both can be overridden:

```sh
BIND_ADDR=127.0.0.1:8080 DATABASE_PATH=/tmp/books.db cargo run
```

## Test

```sh
cargo test
```

## API

| Method   | Path          | Description                          | Success status |
|----------|---------------|--------------------------------------|----------------|
| `GET`    | `/health`     | Health check                         | `200`          |
| `POST`   | `/books`      | Create a book                        | `201`          |
| `GET`    | `/books`      | List books (`?author=` exact filter) | `200`          |
| `GET`    | `/books/{id}` | Get a single book                    | `200`          |
| `PUT`    | `/books/{id}` | Replace a book's fields              | `200`          |
| `DELETE` | `/books/{id}` | Delete a book                        | `204`          |

### Book JSON shape

```json
{
  "id": 1,
  "title": "The Rust Book",
  "author": "Steve Klabnik",
  "year": 2019,
  "isbn": "978-1718500440"
}
```

- `title` and `author` are **required** (non-blank) on `POST` and `PUT`;
  violations return `400` with an `{"error": "..."}` body.
- `year` (integer) and `isbn` (string) are optional.
- Unknown ids return `404`.

### Examples

```sh
# Create
curl -s -X POST http://localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title": "The Rust Book", "author": "Steve Klabnik", "year": 2019, "isbn": "978-1718500440"}'

# List all
curl -s http://localhost:3000/books

# List filtered by author
curl -s 'http://localhost:3000/books?author=Steve%20Klabnik'

# Get one
curl -s http://localhost:3000/books/1

# Update
curl -s -X PUT http://localhost:3000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title": "The Rust Book, 2nd ed.", "author": "Steve Klabnik", "year": 2023}'

# Delete
curl -s -X DELETE http://localhost:3000/books/1 -o /dev/null -w '%{http_code}\n'

# Health
curl -s http://localhost:3000/health
```

## Project layout

```
src/main.rs      — entry point: opens the DB, binds the listener
src/lib.rs       — router construction (build_app)
src/models.rs    — Book and BookInput types
src/db.rs        — SQLite schema + CRUD functions
src/handlers.rs  — HTTP handlers and validation
tests/api_tests.rs — integration tests (in-memory SQLite, no ports)
```
