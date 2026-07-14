# Books API

A REST API service for managing a book collection, written in Rust using
[Axum](https://github.com/tokio-rs/axum) and SQLite (via
[`rusqlite`](https://crates.io/crates/rusqlite)).

## Endpoints

| Method | Path            | Description                          |
|--------|-----------------|--------------------------------------|
| GET    | `/health`       | Health check                         |
| POST   | `/books`        | Create a book                        |
| GET    | `/books`        | List books (supports `?author=`)     |
| GET    | `/books/{id}`   | Get a single book                    |
| PUT    | `/books/{id}`   | Update a book                        |
| DELETE | `/books/{id}`   | Delete a book                        |

### Book shape

```json
{
  "id": 1,
  "title": "The Hobbit",
  "author": "Tolkien",
  "year": 1937,
  "isbn": "123"
}
```

`title` and `author` are required; `year` and `isbn` are optional.

## Setup

Requires a recent Rust toolchain (tested with Rust 1.95).

```sh
cargo build --release
```

## Run

```sh
cargo run --release
```

By default the server listens on `http://0.0.0.0:3000` and persists data
to `books.db` in the working directory. Override with environment
variables:

```sh
HOST=127.0.0.1 PORT=8080 DATABASE_PATH=/tmp/books.db cargo run --release
```

## Tests

```sh
cargo test
```

Includes unit tests for the database layer (`tests/db.rs`) and
integration tests covering the full HTTP flow (`tests/api.rs`): health
check, CRUD lifecycle, input validation, and the `?author=` filter.

## Examples

```sh
# Create
curl -X POST localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Herbert","year":1965,"isbn":"9780441172719"}'

# List
curl localhost:3000/books
curl 'localhost:3000/books?author=Herbert'

# Get / Update / Delete
curl localhost:3000/books/1
curl -X PUT localhost:3000/books/1 -H 'content-type: application/json' -d '{"year":1966}'
curl -X DELETE localhost:3000/books/1
```
