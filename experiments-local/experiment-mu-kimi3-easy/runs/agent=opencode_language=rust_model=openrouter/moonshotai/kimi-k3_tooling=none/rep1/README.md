# book-api

A REST API service for managing a book collection, written in Rust with
[axum](https://docs.rs/axum) and SQLite (via [rusqlite](https://docs.rs/rusqlite),
bundled — no system SQLite required).

## Endpoints

| Method   | Path          | Description                              | Success status |
|----------|---------------|------------------------------------------|----------------|
| `GET`    | `/health`     | Health check                             | `200`          |
| `POST`   | `/books`      | Create a book                            | `201`          |
| `GET`    | `/books`      | List all books; filter with `?author=`   | `200`          |
| `GET`    | `/books/{id}` | Get a single book by ID                  | `200`          |
| `PUT`    | `/books/{id}` | Replace a book                           | `200`          |
| `DELETE` | `/books/{id}` | Delete a book                            | `204`          |

### Book JSON shape

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "978-0441172719"
}
```

- `title` and `author` are **required** (non-blank) — `POST` bodies omit `id`.
- `year` and `isbn` are optional and may be `null`.
- Validation failures return `400`, missing books return `404`, both with a
  JSON body: `{"error": "..."}`.

## Setup

Requires a recent stable Rust toolchain (edition 2021; developed on 1.95).

```sh
cargo build --release
```

## Run

```sh
cargo run
```

Configuration via environment variables:

| Variable        | Default    | Description                                  |
|-----------------|------------|----------------------------------------------|
| `DATABASE_PATH` | `books.db` | SQLite file path (`:memory:` for ephemeral)  |
| `PORT`          | `3000`     | Listen port                                  |

### Examples

```sh
# Create
curl -X POST http://localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'

# List (optionally filtered by author)
curl 'http://localhost:3000/books?author=Frank%20Herbert'

# Get one
curl http://localhost:3000/books/1

# Update
curl -X PUT http://localhost:3000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'

# Delete
curl -X DELETE http://localhost:3000/books/1

# Health check
curl http://localhost:3000/health
```

## Test

```sh
cargo test
```

Integration tests in `tests/api.rs` run the real router against an in-memory
SQLite database via `tower::oneshot` (no ports bound), covering health,
create/get round-trip, input validation, the author filter, update, delete,
and 404 handling.

## Project layout

```
src/
  main.rs     — binary entry point: config, DB open, server startup
  lib.rs      — AppState + router construction (shared with tests)
  models.rs   — Book / BookInput types and validation rules
  db.rs       — SQLite persistence layer (framework-independent)
  handlers.rs — HTTP handlers (thin adapters over db.rs)
  error.rs    — ApiError → (status code, JSON body) mapping
tests/
  api.rs      — integration tests
```
