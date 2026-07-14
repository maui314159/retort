# Book API

A small REST API for managing a book collection, written in Rust with
[`axum`](https://crates.io/crates/axum) and SQLite via
[`rusqlite`](https://crates.io/crates/rusqlite).

## Endpoints

| Method   | Path           | Description                          |
| -------- | -------------- | ------------------------------------ |
| `GET`    | `/health`      | Health check (returns `200 "ok"`)    |
| `POST`   | `/books`       | Create a book                        |
| `GET`    | `/books`       | List books, optional `?author=` filter |
| `GET`    | `/books/:id`   | Get a single book                    |
| `PUT`    | `/books/:id`   | Update a book                        |
| `DELETE` | `/books/:id`   | Delete a book                        |

### Book shape

```json
{
  "id": 1,
  "title": "Rust in Action",
  "author": "Tim McNamara",
  "year": 2017,
  "isbn": "9781617294537",
  "created_at": "2026-06-20 21:14:00"
}
```

`title` and `author` are required (non-empty). `year` and `isbn` are
optional. `isbn` is unique — a duplicate produces `409 Conflict`.

### Status codes

- `200 OK` — successful GET / PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — validation error
- `404 Not Found` — book does not exist
- `409 Conflict` — unique constraint violation (duplicate ISBN)
- `500 Internal Server Error` — unexpected DB error

## Prerequisites

- Rust toolchain (1.75+). Install via <https://rustup.rs>.

## Running

```sh
cargo run --release
```

By default the server listens on `127.0.0.1:8080` and stores data in
`books.db` in the working directory. Override with environment variables:

```sh
BOOK_ADDR=0.0.0.0:3000 BOOK_DB=/tmp/books.db cargo run --release
```

## Examples

```sh
# Create
curl -sS -X POST localhost:8080/books \
  -H 'content-type: application/json' \
  -d '{"title":"Rust in Action","author":"Tim McNamara","year":2017,"isbn":"9781617294537"}'

# List (with optional author filter)
curl -sS 'localhost:8080/books?author=Tim%20McNamara'

# Get one
curl -sS localhost:8080/books/1

# Update
curl -sS -X PUT localhost:8080/books/1 \
  -H 'content-type: application/json' \
  -d '{"year":2018}'

# Delete
curl -sS -X DELETE localhost:8080/books/1 -o /dev/null -w '%{http_code}\n'
```

## Tests

```sh
cargo test
```

The suite uses an in-memory SQLite database and `axum`'s `oneshot`
service tester. Five tests cover: the health endpoint, input validation,
the full create/read/update/delete lifecycle, the `?author=` filter, and
ISBN-uniqueness conflict handling.

## Layout

```
Cargo.toml        # dependencies
src/
  main.rs         # entry point, router, integration tests
  db.rs           # SQLite connection wrapper + schema init
  models.rs       # request/response DTOs
  handlers.rs     # endpoint handlers
  error.rs        # error -> HTTP response mapping
```
