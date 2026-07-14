# Book Collection API

A REST API service for managing a book collection, written in Rust with Axum and SQLite.

## Requirements

- Rust (1.75+ recommended) — https://rustup.rs
- A C compiler for SQLite (clang/gcc; on macOS the Xcode command-line tools suffice)

## Setup

```bash
cargo build
```

The database file (`books.db`) is created automatically on first run.

## Running

```bash
cargo run
```

The server listens on `0.0.0.0:3000`. Override the database location with:

```bash
DATABASE_URL=sqlite:/path/to/books.db cargo run
```

## Endpoints

| Method | Path             | Description                          |
|--------|------------------|--------------------------------------|
| GET    | `/health`        | Health check                         |
| POST   | `/books`         | Create a book                        |
| GET    | `/books`         | List books (supports `?author=`)     |
| GET    | `/books/{id}`    | Get a single book                    |
| PUT    | `/books/{id}`    | Update a book (partial updates ok)   |
| DELETE | `/books/{id}`    | Delete a book                         |

### Book object

```json
{
  "id": 1,
  "title": "The Hobbit",
  "author": "J.R.R. Tolkien",
  "year": 1937,
  "isbn": "978-0261102217"
}
```

`title` and `author` are required; `year` and `isbn` are optional.

## Examples

```bash
# Create
curl -sX POST localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937}'

# List with filter
curl -s 'localhost:3000/books?author=Tolkien'

# Update
curl -sX PUT localhost:3000/books/1 \
  -H 'content-type: application/json' \
  -d '{"year":1938}'

# Delete
curl -sX DELETE localhost:3000/books/1
```

## Tests

```bash
cargo test
```

Tests use an in-memory SQLite database and cover create+get, input validation, list filtering, and delete behavior.
