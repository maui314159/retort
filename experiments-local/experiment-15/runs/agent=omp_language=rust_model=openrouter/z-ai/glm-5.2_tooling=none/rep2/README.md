# Book Collection REST API

A REST API service for managing a book collection, written in Rust.

## Tech stack

- **Language:** Rust (edition 2021)
- **Web framework:** [axum](https://crates.io/crates/axum) 0.8 on [tokio](https://crates.io/crates/tokio)
- **Database:** SQLite via [rusqlite](https://crates.io/crates/rusqlite) (bundled), pooled with [r2d2](https://crates.io/crates/r2d2) / [r2d2_sqlite](https://crates.io/crates/r2d2_sqlite)
- **Serialization:** serde / serde_json
- **Logging:** tracing / tracing-subscriber
- **Errors:** thiserror

## Endpoints

| Method   | Path          | Description                                  |
|----------|---------------|----------------------------------------------|
| `GET`    | `/health`     | Health check (verifies DB connectivity)      |
| `POST`   | `/books`      | Create a new book                            |
| `GET`    | `/books`      | List all books; supports `?author=` filter   |
| `GET`    | `/books/{id}` | Get a single book by ID                      |
| `PUT`    | `/books/{id}` | Update a book (partial update supported)     |
| `DELETE` | `/books/{id}` | Delete a book                                |

### Book shape

```json
{
  "id": 1,
  "title": "The Rust Book",
  "author": "Steve Klabnik",
  "year": 2019,
  "isbn": "9781718500443"
}
```

`title` and `author` are required (non-empty after trimming). `year` and `isbn`
are optional. For `PUT`, only fields you include are changed — but at least one
field must be provided.

### Status codes

- `200 OK` — successful read / update
- `201 Created` — book created
- `204 No Content` — book deleted
- `400 Bad Request` — validation failure (missing/empty title or author, bad year, empty update)
- `404 Not Found` — no book with that ID
- `500 Internal Server Error` — database / pool failure

## Setup & run

Requires a recent Rust toolchain (`rustup` recommended).

```bash
# build
cargo build --release

# run (serves on http://0.0.0.0:3000 by default, persists to ./books.db)
cargo run --release
```

### Configuration via environment variables

| Variable       | Default     | Description                       |
|----------------|-------------|-----------------------------------|
| `BOOK_DB_PATH` | `books.db`  | SQLite database file path         |
| `BOOK_HOST`    | `0.0.0.0`   | Bind address                      |
| `BOOK_PORT`    | `3000`      | Listen port                       |
| `RUST_LOG`     | `info`      | tracing filter (e.g. `debug`)     |

## Example usage

```bash
# create
curl -sX POST localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"The Rust Book","author":"Steve Klabnik","year":2019,"isbn":"9781718500443"}'

# list
curl -s localhost:3000/books

# filter by author
curl -s 'localhost:3000/books?author=klabnik'

# get one
curl -s localhost:3000/books/1

# update (partial)
curl -sX PUT localhost:3000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"The Rust Programming Language"}'

# delete
curl -sX DELETE localhost:3000/books/1 -o /dev/null -w '%{http_code}\n'  # 204

# health
curl -s localhost:3000/health   # {"status":"ok"}
```

## Tests

```bash
cargo test
```

The suite uses an in-memory SQLite database and axum's `tower::ServiceExt`
`oneshot` to exercise the full router end-to-end:

1. `create_get_list_and_delete_book` — full CRUD lifecycle including 404 after delete.
2. `validation_rejects_missing_fields` — missing author, empty title, malformed JSON.
3. `list_filters_by_author` — case-insensitive substring filtering on `?author=`.
4. `update_partial_fields` — partial PUT, empty-update rejection, 404 on missing book.
5. `health_ok` — health endpoint returns `{"status":"ok"}`.
6. `model_validation_unit` — unit tests for `CreateBook`/`UpdateBook` validation rules.

## Project layout

```
src/
  main.rs        # entrypoint: env config, pool, migrate, serve
  lib.rs         # module roots (so tests can import internals)
  router.rs      # axum Router wiring
  handlers.rs    # request handlers + AppState
  db.rs          # pool, migration, CRUD queries
  models.rs      # Book / CreateBook / UpdateBook + validation
  error.rs       # AppError -> HTTP response mapping
tests/
  api.rs         # integration tests
```
