# books-api

A REST API service for managing a book collection, written in Rust with
[Axum](https://github.com/tokio-rs/axum) and SQLite.

## Endpoints

| Method | Path            | Description                              |
|--------|-----------------|------------------------------------------|
| GET    | `/health`       | Liveness probe                           |
| POST   | `/books`        | Create a new book                        |
| GET    | `/books`        | List books (optional `?author=` filter)  |
| GET    | `/books/{id}`   | Fetch a single book                      |
| PUT    | `/books/{id}`   | Update a book                            |
| DELETE | `/books/{id}`   | Delete a book                            |

### Book shape

```json
{
  "id": 1,
  "title": "The Pragmatic Programmer",
  "author": "Andy Hunt",
  "year": 1999,
  "isbn": "978-0201616224"
}
```

`title` and `author` are required. `year` and `isbn` are optional.

### Status codes

| Code | Meaning                                                    |
|------|------------------------------------------------------------|
| 200  | Successful read or update                                  |
| 201  | Book created                                               |
| 204  | Book deleted                                               |
| 400  | Validation error (missing/blank `title` or `author`, etc.) |
| 404  | No book with that id                                       |
| 500  | Internal error                                             |

## Requirements

- Rust 1.75+ (tested on 1.95)
- SQLite (no system library needed — SQLx bundles a Rust-native driver)

## Setup

```bash
# build
cargo build --release

# run (binds 0.0.0.0:3000 by default; uses ./books.db)
./target/release/books-api
```

### Configuration

| Env var       | Default              | Description                       |
|---------------|----------------------|-----------------------------------|
| `DATABASE_URL`| `sqlite://./books.db`| Any URL accepted by SQLx SQLite. |
| `BIND_ADDR`   | `0.0.0.0:3000`       | Socket address to bind.           |
| `RUST_LOG`    | `info`               | `tracing-subscriber` filter.      |

Examples:

```bash
# in-memory database
DATABASE_URL='sqlite::memory:' ./target/release/books-api

# quiet
RUST_LOG=warn ./target/release/books-api
```

## Example session

```bash
# create
curl -X POST http://localhost:3000/books \
     -H 'Content-Type: application/json' \
     -d '{"title":"The Pragmatic Programmer","author":"Andy Hunt","year":1999,"isbn":"978-0201616224"}'

# list
curl http://localhost:3000/books

# filter by author (case-insensitive)
curl 'http://localhost:3000/books?author=martin%20fowler'

# fetch one
curl http://localhost:3000/books/1

# update
curl -X PUT http://localhost:3000/books/1 \
     -H 'Content-Type: application/json' \
     -d '{"title":"The Pragmatic Programmer, 20th Anniversary","author":"Andy Hunt","year":2019}'

# delete
curl -X DELETE http://localhost:3000/books/1

# health
curl http://localhost:3000/health
```

## Tests

```bash
cargo test
```

The suite includes 4 unit tests for input validation and 6 integration
tests that drive the full router against an in-memory SQLite database
(unique per test, so they can run in parallel):

- `health_endpoint_returns_ok`
- `crud_lifecycle_round_trip` (POST → GET → PUT → DELETE → 404)
- `list_books_and_filter_by_author`
- `validation_rejects_missing_required_fields`
- `not_found_for_missing_resources`
- `invalid_id_returns_400`

## Project layout

```
src/
  main.rs       # binary entry point
  lib.rs        # exposes `build_app` and module tree
  error.rs      # `AppError` + IntoResponse mapping to HTTP status
  models.rs     # `Book`, `NewBook`, `BookUpdate` + validation
  db.rs         # SQLite pool, schema migration, queries
  handlers.rs   # axum handlers + `AppState`
tests/
  integration.rs
```

## Notes

- The SQLite schema is created on startup (`CREATE TABLE IF NOT EXISTS`)
  and the `books(author)` index is added in the same migration.
- `PUT` replaces the entire resource — `title` and `author` are required,
  and absent fields are normalized to `NULL` on the stored row.
- The `?author=` filter is a case-insensitive exact match; an empty value
  (`?author=`) is treated as "no filter" for convenience.
