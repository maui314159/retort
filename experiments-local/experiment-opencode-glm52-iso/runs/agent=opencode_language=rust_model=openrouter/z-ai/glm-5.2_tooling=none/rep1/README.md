# Books API

A REST API service for managing a book collection, written in Rust using
[Axum](https://github.com/tokio-rs/axum) and SQLite (via
[`rusqlite`](https://crates.io/crates/rusqlite)).

## Endpoints

| Method   | Path          | Description                          |
| -------- | ------------- | ------------------------------------ |
| `GET`    | `/health`     | Health check                         |
| `POST`   | `/books`      | Create a new book                    |
| `GET`    | `/books`      | List all books (supports `?author=`) |
| `GET`    | `/books/{id}` | Get a single book by ID              |
| `PUT`    | `/books/{id}` | Update a book                        |
| `DELETE` | `/books/{id}` | Delete a book                        |

### Book shape

```json
{
  "id": 1,
  "title": "The Hobbit",
  "author": "J.R.R. Tolkien",
  "year": 1937,
  "isbn": "978-0261102217"
}
```

`title` and `author` are required; `year` and `isbn` are optional. Creating or
updating a book without a non-empty `title`/`author` returns `400 Bad Request`.

## Setup

Requires a recent Rust toolchain (edition 2021, tested on Rust 1.95).

```bash
cargo build --release
```

## Run

```bash
cargo run --release
# or
DB_PATH=/path/to/books.db cargo run --release
```

The server listens on `0.0.0.0:3000` by default. The SQLite database file
defaults to `./books.db` and can be overridden with the `DB_PATH` environment
variable.

## Examples

Create a book:

```bash
curl -X POST http://localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
```

List books, optionally filtered by author:

```bash
curl 'http://localhost:3000/books?author=Frank%20Herbert'
```

Get / update / delete:

```bash
curl http://localhost:3000/books/1
curl -X PUT http://localhost:3000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"Dune (Updated)","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl -X DELETE http://localhost:3000/books/1
```

## Tests

Unit/integration tests live in `src/main.rs` and exercise the router end-to-end
via `tower::ServiceExt::oneshot` against an in-memory SQLite database.

```bash
cargo test
```

The suite covers:

- `create_and_get_book` — POST then GET returns the created book.
- `full_crud_lifecycle` — create, read, update, list-with-filter, delete, and
  confirms the deleted book returns `404`.
- `validation_errors` — missing `title` or `author` return `400 Bad Request`.
- `health_ok` — the `/health` endpoint returns `200 OK`.

## Status codes

| Code | Meaning                                  |
| ---- | ---------------------------------------- |
| 200  | Success (GET, PUT)                       |
| 201  | Created (POST)                           |
| 204  | No content (DELETE)                      |
| 400  | Validation error                         |
| 404  | Book not found                           |
| 500  | Internal server / database error         |
