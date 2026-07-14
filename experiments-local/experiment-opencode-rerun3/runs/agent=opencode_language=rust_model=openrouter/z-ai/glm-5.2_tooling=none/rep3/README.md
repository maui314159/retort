# Books API

A small REST API for managing a book collection, written in Rust with
[axum](https://github.com/tokio-rs/axum) and [sqlx](https://github.com/launchbadge/sqlx)
backed by an embedded SQLite database.

## Endpoints

| Method | Path            | Description                          |
|--------|-----------------|--------------------------------------|
| GET    | `/health`       | Health check                         |
| POST   | `/books`        | Create a book                        |
| GET    | `/books`        | List books (supports `?author=`)     |
| GET    | `/books/{id}`   | Get a single book                    |
| PUT    | `/books/{id}`   | Update a book (partial/merge update) |
| DELETE | `/books/{id}`   | Delete a book                        |

### Book shape

```json
{
  "id": 1,
  "title": "The Pragmatic Programmer",
  "author": "Hunt & Thomas",
  "year": 1999,
  "isbn": "9780201616224",
  "created_at": "2026-06-20T23:53:00Z"
}
```

`title` and `author` are required. `year` and `isbn` are optional.
`isbn` is unique across books.

### Status codes

- `200 OK` — successful GET / PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — validation failure (e.g. empty title/author)
- `404 Not Found` — book with given id does not exist
- `409 Conflict` — duplicate ISBN
- `500 Internal Server Error` — unexpected failure

## Setup

Requires Rust 1.75+ (stable).

```bash
cargo build --release
```

## Run

```bash
cargo run --release
# listens on 0.0.0.0:3000
```

Configure via environment variables:

- `DATABASE_URL` — SQLite connection string. Default:
  `sqlite:books.db?mode=rwc` (a file `books.db` is created in the cwd).
- `LISTEN_ADDR` — bind address. Default: `0.0.0.0:3000`.

### Quick check

```bash
curl -s http://localhost:3000/health
# {"status":"ok"}

curl -s -X POST http://localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"The Pragmatic Programmer","author":"Hunt","year":1999,"isbn":"9780201616224"}'

curl -s 'http://localhost:3000/books?author=Hunt'
```

## Tests

Integration tests spin up isolated SQLite databases in the OS temp
directory and exercise the full HTTP stack via `tower::ServiceExt`:

```bash
cargo test
```

This covers: health check, the full create/list/get/update/delete
lifecycle, input validation (empty + missing required fields), and the
unique-ISBN constraint.
