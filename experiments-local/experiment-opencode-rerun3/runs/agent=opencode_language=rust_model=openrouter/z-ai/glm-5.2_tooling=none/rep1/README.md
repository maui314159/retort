# books-api

A small REST API service for managing a book collection, written in Rust with
[`axum`](https://docs.rs/axum) and [`sqlx`](https://docs.rs/sqlx) backed by an
embedded SQLite database.

## Endpoints

| Method & path          | Description                          | Status codes          |
|------------------------|--------------------------------------|-----------------------|
| `GET  /health`        | Liveness probe                        | 200                   |
| `POST /books`         | Create a book                         | 201, 400              |
| `GET  /books`          | List books (`?author=` filter)        | 200                   |
| `GET  /books/{id}`    | Get a single book                    | 200, 404              |
| `PUT  /books/{id}`    | Update a book (full replace)         | 200, 400, 404         |
| `DELETE /books/{id}` | Delete a book                        | 204, 404              |

### Book body shape

```json
{
  "title": "required, non-empty",
  "author": "required, non-empty",
  "year": 2024,
  "isbn": "978-..."
}
```

`year` and `isbn` are optional and may be omitted or `null`. `title` and
`author` are required and must not be blank; otherwise the server replies
`400 Bad Request` with a JSON `{"error": "..."}` body. All responses are JSON.

## Setup & run

Requirements: a recent Rust toolchain (the project uses edition 2024).

```bash
# Build
cargo build --release

# Run (uses ./books.db as the database by default, created on first run)
cargo run --release

# Use a custom database location or address
DATABASE_URL="sqlite:./books.db?mode=rwc" LISTEN_ADDR="127.0.0.1:8080" cargo run --release
```

SQLite is compiled and statically linked into the binary (via the
`bundled` feature of `libsqlite3-sys`), so there is no runtime dependency on a
system `libsqlite3`.

### Quick examples

```bash
# Create
curl -s -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Foundation","author":"Asimov","year":1951,"isbn":"978-0"}'

# List
curl -s http://localhost:3000/books
curl -s 'http://localhost:3000/books?author=Asimov'

# Get / update / delete
curl -s http://localhost:3000/books/1
curl -s -X PUT http://localhost:3000/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Foundation","author":"Asimov","year":1951}'
curl -i -X DELETE http://localhost:3000/books/1
```

## Tests

The project ships four integration tests under `tests/books_api.rs` covering
the health check, the full create/get/list/update/delete lifecycle, input
validation (missing and empty required fields), and the `?author=` filter:

```bash
cargo test
```

## Project layout

```
src/
  lib.rs        # module wiring (also used by tests)
  models.rs     # Book + BookInput (with validation helper)
  error.rs      # AppError -> (StatusCode, JSON) mapping
  db.rs         # SQLite schema initialization
  handlers.rs   # axum router + route handlers (state: SqlitePool)
  main.rs       # binary entrypoint: open pool, init schema, serve
tests/
  books_api.rs  # integration tests (reqwest against a live ephemeral server)
```
