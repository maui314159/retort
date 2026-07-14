# Book Collection API

A small REST API for managing a book collection, written in Rust with [Axum](https://github.com/tokio-rs/axum) and SQLite.

## Endpoints

| Method | Path           | Description                          |
|--------|----------------|--------------------------------------|
| GET    | `/health`      | Health check                         |
| GET    | `/books`       | List all books (optional `?author=`) |
| POST   | `/books`       | Create a new book                    |
| GET    | `/books/{id}`  | Get a single book by ID              |
| PUT    | `/books/{id}`  | Update a book                        |
| DELETE | `/books/{id}`  | Delete a book                        |

## Running

```bash
cargo run
```

The server listens on `0.0.0.0:3000`. By default it writes to `books.db` in the working directory. You can override the database path with the `DATABASE_PATH` environment variable:

```bash
DATABASE_PATH=/tmp/books.db cargo run
```

## Testing

```bash
cargo test
```

The test suite includes health-check, CRUD, filtering, and validation tests.
