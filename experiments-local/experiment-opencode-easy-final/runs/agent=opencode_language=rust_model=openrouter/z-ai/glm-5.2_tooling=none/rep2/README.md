# Books API

A small REST API for managing a book collection, written in Rust with
[Axum](https://github.com/tokio-rs/axum) and [SQLx](https://github.com/launchbadge/sqlx)
backed by embedded SQLite.

## Endpoints

| Method   | Path          | Description                                  |
| -------- | ------------- | -------------------------------------------- |
| `GET`    | `/health`     | Health check (returns `ok`)                  |
| `POST`   | `/books`      | Create a new book                            |
| `GET`    | `/books`      | List all books (optional `?author=` filter)  |
| `GET`    | `/books/:id`  | Get a single book                            |
| `PUT`    | `/books/:id`  | Update a book (partial update supported)     |
| `DELETE` | `/books/:id`  | Delete a book                                |

### Book model

```json
{
  "id": 1,
  "title": "The Hobbit",
  "author": "J.R.R. Tolkien",
  "year": 1937,
  "isbn": "9780261103283"
}
```

`title` and `author` are required and must be non-empty. `year` and `isbn`
are optional. `PUT` accepts any subset of the fields.

## Setup

Requires a recent Rust toolchain (tested on 1.95).

```sh
cargo build
```

## Run

```sh
cargo run
```

The server listens on `0.0.0.0:3000`. Override the database location with
the `DATABASE_URL` environment variable (defaults to `sqlite:books.db`):

```sh
DATABASE_URL=sqlite:books.db cargo run
```

### Examples

```sh
# Create
curl -sS localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937}'

# List
curl -sS localhost:3000/books
curl -sS 'localhost:3000/books?author=Tolkien'

# Get / update / delete
curl -sS localhost:3000/books/1
curl -sS -X PUT localhost:3000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"There and Back Again"}'
curl -sS -X DELETE localhost:3000/books/1
```

## Tests

```sh
cargo test
```

The integration tests in `tests/api.rs` spin up an in-memory SQLite server
on an ephemeral port and exercise the full CRUD flow, input validation,
the author filter, and the health endpoint.

## Layout

```
src/main.rs   binary entrypoint
src/lib.rs    all handlers, DB layer, router, pool setup
tests/api.rs  HTTP integration tests
```
