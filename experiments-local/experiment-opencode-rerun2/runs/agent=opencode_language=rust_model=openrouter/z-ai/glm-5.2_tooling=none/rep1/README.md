# Books API

A small REST API for managing a book collection, written in Rust with
[`axum`](https://crates.io/crates/axum), [`sqlx`](https://crates.io/crates/sqlx)
and SQLite as the embedded database.

## Endpoints

| Method   | Path          | Description                          |
|----------|---------------|--------------------------------------|
| `GET`    | `/health`     | Health check                         |
| `POST`   | `/books`      | Create a new book                    |
| `GET`    | `/books`      | List all books (`?author=` filter)   |
| `GET`    | `/books/{id}` | Get a single book                    |
| `PUT`    | `/books/{id}` | Update a book (partial updates ok)   |
| `DELETE` | `/books/{id}` | Delete a book                        |

### Book payload

```json
{
  "title": "The Rust Book",
  "author": "Steve Klabnik",
  "year": 2020,
  "isbn": "978-1593278281"
}
```

`title` and `author` are required and must be non-empty. `year` and `isbn` are
optional.

## Requirements

- Rust 1.75+ (tested with 1.95)
- A C compiler for SQLite (bundled by `sqlx` is *not* enabled here; the system
  `libsqlite3` is used via the `sqlite` feature — on macOS/Linux this ships with
  the OS). If you need a self-contained build, add the `sqlx` feature
  `sqlite-unbundled` -> `sqlite-bundled` in `Cargo.toml`.

## Setup

```bash
cargo build
```

## Run

```bash
cargo run
```

By default the server listens on `0.0.0.0:3000` and writes to `./books.db`.
Override with environment variables:

```bash
DATABASE_URL="sqlite:books.db?mode=rwc" LISTEN_ADDR="127.0.0.1:8080" cargo run
```

The database schema is created automatically on startup via `sqlx::migrate!`
from `migrations/`.

## Examples

```bash
# Create a book
curl -sX POST localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"T","author":"A","year":2020}'

# List
curl -s localhost:3000/books
curl -s 'localhost:3000/books?author=A'

# Get / update / delete
curl -s localhost:3000/books/1
curl -sX PUT localhost:3000/books/1 -H 'content-type: application/json' -d '{"year":2021}'
curl -sX DELETE localhost:3000/books/1
```

## Tests

```bash
cargo test
```

Integration tests live in `tests/api.rs` and use an in-memory SQLite database.
They cover: create/get/delete flow, listing with `?author=` filter, input
validation (missing/empty `title` and `author`), partial `PUT` updates, and the
health check.
