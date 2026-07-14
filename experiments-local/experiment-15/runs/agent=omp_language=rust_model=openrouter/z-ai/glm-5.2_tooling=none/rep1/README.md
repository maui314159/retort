# Book Collection API

A small REST API for managing a book collection, written in Rust with
[`axum`](https://docs.rs/axum) and SQLite (via [`sqlx`](https://docs.rs/sqlx)).

## Endpoints

| Method   | Path          | Description                              |
|----------|---------------|------------------------------------------|
| `GET`    | `/health`     | Health check (returns `200 ok`)          |
| `POST`   | `/books`      | Create a new book                         |
| `GET`    | `/books`      | List all books (optional `?author=` filter) |
| `GET`    | `/books/{id}` | Get a single book by ID                  |
| `PUT`    | `/books/{id}` | Update a book                            |
| `DELETE` | `/books/{id}` | Delete a book                            |

### Book object

```json
{
  "id": 1,
  "title": "The Hobbit",
  "author": "J.R.R. Tolkien",
  "year": 1937,
  "isbn": "9780261103283",
  "created_at": "2026-06-20T10:00:00",
  "updated_at": "2026-06-20T10:00:00"
}
```

- `title` and `author` are **required** and must be non-empty (after trimming).
- `year` and `isbn` are optional.

### Status codes

| Code | Meaning                                           |
|------|---------------------------------------------------|
| 200  | OK (GET, PUT)                                     |
| 201  | Created (POST)                                    |
| 204  | No Content (DELETE)                               |
| 400  | Bad Request — validation error (empty title/author) |
| 404  | Not Found — book with given ID does not exist     |
| 422  | Unprocessable Entity — malformed/missing JSON field |
| 500  | Internal Server Error                             |

## Setup

Requires a recent Rust toolchain (`cargo` 1.74+).

```bash
cargo build
```

## Run

```bash
cargo run
```

By default the service listens on `0.0.0.0:3000` and stores data in
`books.db` (created automatically) in the working directory.

Configuration via environment variables:

| Variable       | Default                      | Description                          |
|----------------|------------------------------|--------------------------------------|
| `LISTEN_ADDR`  | `0.0.0.0:3000`               | Bind address for the HTTP server     |
| `DATABASE_URL` | `sqlite:books.db?mode=rwc`   | sqlx SQLite connection string        |
| `RUST_LOG`     | `info`                       | `tracing` log level                  |

To use an in-memory database (e.g. for quick experiments):

```bash
DATABASE_URL="sqlite::memory:" cargo run
```

## Examples

Create a book:

```bash
curl -sX POST http://localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937,"isbn":"9780261103283"}'
```

List all books:

```bash
curl -s http://localhost:3000/books
```

Filter by author (substring match):

```bash
curl -s 'http://localhost:3000/books?author=Tolkien'
```

Get / update / delete:

```bash
curl -s  http://localhost:3000/books/1
curl -sX PUT http://localhost:3000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1938}'
curl -sX DELETE http://localhost:3000/books/1
```

## Tests

The integration tests in [`tests/api.rs`](tests/api.rs) spin up an isolated
in-memory SQLite database and exercise the full HTTP router via axum's
`tower::ServiceExt` test utilities.

```bash
cargo test
```

Test coverage:

1. `create_get_and_list_book` — POST, GET (list), GET by id.
2. `validation_rejects_empty_title_and_author` — empty title (400) and
   missing required field (422).
3. `update_then_delete_book` — PUT, DELETE, and 404 on missing resource.
4. `author_filter_works` — `?author=` query filter.
5. `health_check_ok` — `/health` returns 200.

## Project layout

```
src/
  main.rs      # entrypoint: builds pool, router, serves app
  lib.rs       # re-exports modules for tests
  db.rs        # schema initialization
  models.rs    # Book / BookInput types + validation
  error.rs     # ApiError -> HTTP response mapping
  handlers.rs  # route definitions and request handlers
tests/
  api.rs       # integration tests
```
