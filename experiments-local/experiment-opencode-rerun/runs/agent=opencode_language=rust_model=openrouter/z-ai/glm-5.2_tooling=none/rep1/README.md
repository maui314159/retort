# Book Collection API

A small REST API service for managing a book collection, written in Rust.

## Tech stack

- **Language:** Rust (edition 2021)
- **Web framework:** [axum](https://crates.io/crates/axum) 0.8
- **Database:** SQLite via [rusqlite](https://crates.io/crates/rusqlite) (bundled `libsqlite3`, so no system SQLite required)
- **Async runtime:** tokio
- **Logging:** tracing / tracing-subscriber
- **Error handling:** thiserror + anyhow

## Endpoints

| Method | Path            | Description                                   |
|--------|-----------------|-----------------------------------------------|
| GET    | `/health`       | Health check                                  |
| POST   | `/books`        | Create a new book                             |
| GET    | `/books`        | List all books (supports `?author=` filter)   |
| GET    | `/books/{id}`   | Get a single book by ID                       |
| PUT    | `/books/{id}`   | Update a book (partial update supported)      |
| DELETE | `/books/{id}`   | Delete a book                                 |

### Book model

```json
{
  "id": 1,
  "title": "The Rust Book",
  "author": "Jane Doe",
  "year": 2021,
  "isbn": "978-3-16-148410-0"
}
```

- `title` and `author` are **required** (non-empty). Validation returns `400 Bad Request`.
- `year` and `isbn` are optional.
- Unknown IDs return `404 Not Found`.
- Missing/invalid JSON fields return `422 Unprocessable Entity` (axum's `Json` extractor).

### Status codes

- `200 OK` — successful GET / PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — validation failure
- `404 Not Found` — book does not exist
- `422 Unprocessable Entity` — malformed request body
- `500 Internal Server Error` — unexpected database/internal error

## Setup & run

### Prerequisites

- Rust toolchain (rustup recommended). Tested with Rust 1.95.

### Build

```sh
cargo build --release
```

### Run

```sh
cargo run --release
```

By default the service listens on `0.0.0.0:3000` and stores data in `./books.db`.
Both are configurable via environment variables:

```sh
BOOK_API_ADDR=127.0.0.1:8080 \
BOOK_DB_PATH=/var/lib/book-api/data.db \
cargo run --release
```

### Example requests

```sh
# Create
curl -sX POST http://localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"The Rust Book","author":"Jane Doe","year":2021,"isbn":"978-3-16-148410-0"}'

# List all
curl -s http://localhost:3000/books

# Filter by author
curl -s 'http://localhost:3000/books?author=Jane%20Doe'

# Get one
curl -s http://localhost:3000/books/1

# Update
curl -sX PUT http://localhost:3000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"The Rust Book, 2nd Ed."}'

# Delete
curl -sX DELETE http://localhost:3000/books/1

# Health
curl -s http://localhost:3000/health
```

## Tests

```sh
cargo test
```

The test suite is in [`tests/integration.rs`](tests/integration.rs) and exercises the full
HTTP stack end-to-end against an in-memory SQLite database:

1. `create_list_get_update_delete_flow` — full CRUD lifecycle.
2. `validation_requires_title_and_author` — input validation returns 400/422.
3. `author_filter_works` — the `?author=` query filter.
4. `health_check_ok` — health endpoint.
5. `get_missing_book_returns_404` — 404 handling.

## Project layout

```
src/
  main.rs       # binary entry point: wires router, tracing, TCP listener
  lib.rs        # library: exposes app_router + modules (used by tests)
  db.rs         # Db wrapper around rusqlite Connection (Mutex<Connection>)
  handlers.rs   # axum route handlers
  models.rs     # Book / CreateBook / UpdateBook + validation
  error.rs      # AppError -> HTTP response mapping
tests/
  integration.rs
```
