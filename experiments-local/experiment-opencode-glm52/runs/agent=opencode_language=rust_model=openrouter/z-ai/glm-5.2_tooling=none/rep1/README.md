# Book Collection API

A small REST API for managing a book collection, written in Rust with
[`axum`](https://docs.rs/axum) and [`rusqlite`](https://docs.rs/rusqlite)
(SQLite via the bundled C library — no system SQLite required).

## Endpoints

| Method   | Path          | Description                                  |
| -------- | ------------- | -------------------------------------------- |
| `GET`    | `/health`     | Health check                                 |
| `POST`   | `/books`      | Create a new book                            |
| `GET`    | `/books`      | List all books (supports `?author=` filter)  |
| `GET`    | `/books/:id`  | Get a single book by ID                      |
| `PUT`    | `/books/:id`  | Update a book (partial updates supported)    |
| `DELETE` | `/books/:id`  | Delete a book                                |

### Book shape

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "The Pragmatic Programmer",
  "author": "Hunt & Thomas",
  "year": 1999,
  "isbn": "978-0201616224"
}
```

- `id` is a server-generated UUIDv4.
- `title` and `author` are **required** (non-empty).
- `year` and `isbn` are optional.

### Status codes

- `200 OK` — successful read / update
- `201 Created` — successful create
- `204 No Content` — successful delete
- `400 Bad Request` — validation failure (missing/blank `title`/`author`, etc.)
- `404 Not Found` — book with the given `id` does not exist
- `500 Internal Server Error` — unexpected failure

## Setup & run

Requires Rust (stable, 1.75+) and `cargo`.

```sh
# Debug build, runs on 127.0.0.1:8080, persists to ./books.db
cargo run

# Or pick a custom bind address / db path
BOOKS_ADDR=0.0.0.0:9000 BOOKS_DB_PATH=/tmp/books.db cargo run --release
```

SQLite is bundled via `rusqlite`'s `bundled` feature, so no system packages
are required.

## Example session

```sh
# Create
curl -s localhost:8080/books \
  -H 'content-type: application/json' \
  -d '{"title":"Tao Te Ching","author":"Laozi","year":-600}' | jq

# List all
curl -s localhost:8080/books | jq

# List with author filter
curl -s 'localhost:8080/books?author=Laozi' | jq

# Get one
curl -s localhost:8080/books/<ID> | jq

# Update
curl -s -X PUT localhost:8080/books/<ID> \
  -H 'content-type: application/json' \
  -d '{"year":-500}' | jq

# Delete
curl -s -o /dev/null -w '%{http_code}\n' -X DELETE localhost:8080/books/<ID>
```

## Tests

The suite includes unit tests for the data layer and integration tests that
boot the full HTTP server on an ephemeral port with a temporary SQLite file:

```sh
cargo test
```

Lints:

```sh
cargo clippy --all-targets
```

## Layout

```
src/
  main.rs       # binary entrypoint (reads env, starts server)
  lib.rs        # crate root, re-exports
  db.rs         # rusqlite-backed Book store
  error.rs      # AppError + JsonRequest (400-on-malformed-body extractor)
  handlers.rs   # axum router + route handlers
  models.rs     # serde DTOs (Book, CreateBook, UpdateBook)
tests/
  api_tests.rs  # integration + unit tests
```
