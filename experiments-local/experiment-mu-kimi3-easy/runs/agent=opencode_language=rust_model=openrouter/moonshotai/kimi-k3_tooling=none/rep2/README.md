# Book Collection API

A REST API service for managing a book collection, written in Rust with
[axum](https://github.com/tokio-rs/axum) and SQLite (via
[`rusqlite`](https://github.com/rusqlite/rusqlite) with the bundled SQLite
library — no external database server needed).

## Endpoints

| Method   | Path          | Description                                       |
|----------|---------------|---------------------------------------------------|
| `GET`    | `/health`     | Health check → `{"status":"ok"}`                  |
| `POST`   | `/books`      | Create a new book                                 |
| `GET`    | `/books`      | List all books; `?author=` filters by author      |
| `GET`    | `/books/{id}` | Get a single book by ID                           |
| `PUT`    | `/books/{id}` | Replace all fields of a book                      |
| `DELETE` | `/books/{id}` | Delete a book                                     |

### Book JSON shape

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719" }
```

- `title` and `author` are **required** (validated; blank values are rejected).
- `year` and `isbn` are optional (`null` when absent).

### Status codes

| Code | Meaning                                                        |
|------|----------------------------------------------------------------|
| 200  | Success (`GET`, `PUT`)                                         |
| 201  | Created (`POST /books`)                                        |
| 204  | Deleted (`DELETE /books/{id}`, empty body)                     |
| 400  | Validation failed / malformed JSON — `{"error":"..."}`         |
| 404  | Book not found — `{"error":"book <id> not found"}`             |
| 422  | Missing required field or wrong JSON types                     |
| 500  | Server-side error                                              |

## Setup

Requires a Rust toolchain (2021 edition; 1.75+ recommended) — install via
<https://rustup.rs>. Then:

```sh
cargo build --release
```

## Run

```sh
cargo run            # or: ./target/release/book-collection-api
```

The server listens on `http://127.0.0.1:3000` and stores data in `books.db` in
the working directory. Both are configurable via environment variables:

```sh
BIND_ADDR=0.0.0.0:8080 DATABASE_PATH=/data/books.db cargo run
```

## Examples

```sh
# Health check
curl http://127.0.0.1:3000/health

# Create a book
curl -X POST http://127.0.0.1:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

# List all books / filter by author
curl http://127.0.0.1:3000/books
curl "http://127.0.0.1:3000/books?author=Frank%20Herbert"

# Get one book
curl http://127.0.0.1:3000/books/1

# Update a book
curl -X PUT http://127.0.0.1:3000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"Dune (reissue)","author":"Frank Herbert","year":1990}'

# Delete a book
curl -X DELETE http://127.0.0.1:3000/books/1
```

## Test

```sh
cargo test
```

This runs 10 tests: unit tests for the SQLite layer (`src/db.rs`) and
end-to-end integration tests (`tests/integration.rs`) that exercise the real
HTTP router against an in-memory database — covering creation, retrieval,
listing with the author filter, updates, deletion, health check, and
validation/error status codes.

## Project layout

```
src/
  main.rs       — binary entry point (binds a TCP listener, serves the router)
  lib.rs        — app state, DB initialization, router construction
  models.rs     — Book / BookInput / ErrorResponse types
  db.rs         — SQLite queries (+ unit tests)
  handlers.rs   — HTTP handlers for each endpoint
  error.rs      — ApiError → JSON error responses with status codes
tests/
  integration.rs — in-process end-to-end tests
```
