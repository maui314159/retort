# Book API

A REST API service for managing a book collection, written in Rust using
[Axum](https://github.com/tokio-rs/axum) and SQLite (via `rusqlite` + an
`r2d2` connection pool).

## Endpoints

| Method | Path           | Description                          |
|--------|----------------|--------------------------------------|
| GET    | `/health`      | Health check                         |
| POST   | `/books`       | Create a new book                    |
| GET    | `/books`       | List all books (supports `?author=`) |
| GET    | `/books/{id}`  | Get a single book by ID              |
| PUT    | `/books/{id}`  | Update a book                        |
| DELETE | `/books/{id}`  | Delete a book                        |

### Book JSON shape

```json
{
  "id": 1,
  "title": "The Hobbit",
  "author": "J.R.R. Tolkien",
  "year": 1937,
  "isbn": "978-0261102217"
}
```

`title` and `author` are required and must be non-empty. `year` (integer)
and `isbn` (string) are optional.

## Setup

Requires Rust (edition 2021, tested with 1.95) and Cargo.

```sh
cargo build
```

## Run

```sh
cargo run
```

The server listens on `0.0.0.0:3000`. The SQLite database path defaults to
`books.db` in the working directory; override it with the `DATABASE_URL`
environment variable:

```sh
DATABASE_URL=/tmp/mybooks.db cargo run
```

### Example requests

```sh
# Health check
curl -s http://localhost:3000/health

# Create a book
curl -s -X POST http://localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"The Hobbit","author":"Tolkien","year":1937,"isbn":"123"}'

# List all books
curl -s http://localhost:3000/books

# List books by author
curl -s 'http://localhost:3000/books?author=Tolkien'

# Get a book
curl -s http://localhost:3000/books/1

# Update a book
curl -s -X PUT http://localhost:3000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"New Title","author":"New Author"}'

# Delete a book
curl -s -X DELETE http://localhost:3000/books/1
```

## Tests

Unit/integration tests live in `tests/api.rs` and use axum's `oneshot` test
utility against the in-memory router:

```sh
cargo test
```
