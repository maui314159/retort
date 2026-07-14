# Book Collection API

A small REST API service for managing a book collection, written in Rust with Axum and SQLite.

## Features

- `GET /health` — health check
- `POST /books` — create a new book
- `GET /books` — list all books, optionally filtered by `?author=`
- `GET /books/{id}` — get a single book
- `PUT /books/{id}` — update a book
- `DELETE /books/{id}` — delete a book

## Requirements

- [Rust](https://rustup.rs/) 1.70 or later

## Run

```bash
cargo run
```

The server starts on `http://0.0.0.0:3000` and writes data to `books.db` by default. Override the database path with:

```bash
DATABASE_PATH=my.db cargo run
```

## Test

```bash
cargo test
```

## Example usage

Create a book:

```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937,"isbn":"978-0-00-000000-0"}'
```

List books by author:

```bash
curl "http://localhost:3000/books?author=J.R.R.%20Tolkien"
```
