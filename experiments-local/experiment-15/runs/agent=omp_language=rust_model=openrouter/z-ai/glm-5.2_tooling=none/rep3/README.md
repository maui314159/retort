# Book Collection REST API

A small REST API for managing a book collection, written in Rust with
[`axum`](https://docs.rs/axum) and [`rusqlite`](https://docs.rs/rusqlite)
(bundled SQLite — no system SQLite install required).

## Endpoints

| Method   | Path           | Description                          |
|----------|----------------|--------------------------------------|
| `GET`    | `/health`      | Health check                         |
| `POST`   | `/books`       | Create a new book                    |
| `GET`    | `/books`       | List all books (supports `?author=`) |
| `GET`    | `/books/{id}`  | Get a single book by ID              |
| `PUT`    | `/books/{id}`  | Update a book                        |
| `DELETE` | `/books/{id}`  | Delete a book                        |

### Book shape

```json
{
  "id": 1,
  "title": "The Pragmatic Programmer",
  "author": "Andrew Hunt",
  "year": 1999,
  "isbn": "978-0201616224"
}
```

`title` and `author` are required and must be non-empty. `year` and `isbn`
are optional.

## Setup & run

Requires Rust (stable). No external database needed — SQLite is bundled.

```bash
# build and run (serves on http://0.0.0.0:3000)
cargo run --release
```

The server writes a `books.db` SQLite file in the working directory on first
run.

### Example

```bash
# create a book
curl -sS -X POST http://localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"T","author":"A","year":2000}' | jq

# list
curl -sS http://localhost:3000/books | jq

# filter by author
curl -sS 'http://localhost:3000/books?author=A' | jq
```

## Tests

```bash
cargo test
```

Includes:

- `tests/validation.rs` — unit tests for input validation.
- `tests/api.rs` — integration tests covering create/get/list-with-filter,
  update, delete, health check, and validation-error responses (5 tests),
  exercising the full HTTP stack via `tower::ServiceExt` against an in-memory
  SQLite database.

## Project layout

```
src/
  main.rs       # binary entrypoint (binds 0.0.0.0:3000, opens books.db)
  lib.rs        # router + AppState
  db.rs         # SQLite data access
  models.rs     # Book + input validation
  handlers.rs   # axum route handlers
  error.rs      # ApiError -> HTTP response mapping
tests/
  api.rs        # HTTP integration tests
  validation.rs # validation unit tests
```
