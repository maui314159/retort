# books-api

A small REST API service for managing a book collection, written in Rust with
[`axum`](https://docs.rs/axum) and SQLite (via
[`rusqlite`](https://docs.rs/rusqlite), bundled).

## Features

- `POST /books` — create a book (`title`, `author`, `year`, `isbn`)
- `GET /books` — list all books, supports `?author=` filter
- `GET /books/{id}` — fetch a single book
- `PUT /books/{id}` — update a book (partial update supported)
- `DELETE /books/{id}` — delete a book
- `GET /health` — health check returning `{"status":"ok"}`

Input validation: `title` and `author` are required and must not be blank.

## Prerequisites

- Rust toolchain (1.75+ recommended). Install via <https://rustup.rs>.

No external SQLite library is required — `rusqlite` is built with the `bundled`
feature, which compiles SQLite from source.

## Setup & run

```bash
# from the project root
cargo run --release
```

By default the service listens on `0.0.0.0:3000` and stores data in
`books.db` in the current working directory.

### Configuration via environment variables

| Variable        | Default        | Description                          |
| --------------- | -------------- | ------------------------------------ |
| `BOOKS_BIND_ADDR` | `0.0.0.0:3000` | Address the HTTP server binds to     |
| `BOOKS_DB_PATH` | `books.db`     | Path to the SQLite database file     |

Example:

```bash
BOOKS_BIND_ADDR=127.0.0.1:8080 BOOKS_DB_PATH=/tmp/books.db cargo run --release
```

## API examples

Create a book:

```bash
curl -sS -X POST http://localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"The Rust Book","author":"Steve Klabnik","year":2019,"isbn":"9781593278282"}'
```

List all books:

```bash
curl -sS http://localhost:3000/books
```

Filter by author:

```bash
curl -sS 'http://localhost:3000/books?author=Steve%20Klabnik'
```

Get / update / delete:

```bash
curl -sS http://localhost:3000/books/1
curl -sS -X PUT http://localhost:3000/books/1 \
  -H 'content-type: application/json' \
  -d '{"year":2020}'
curl -sS -X DELETE http://localhost:3000/books/1
```

Health check:

```bash
curl -sS http://localhost:3000/health
```

### HTTP status codes

| Status | Meaning                                  |
| ------ | ---------------------------------------- |
| 200    | OK (GET, PUT)                            |
| 201    | Created (POST)                           |
| 204    | No Content (DELETE)                      |
| 400    | Bad Request — validation error           |
| 404    | Not Found — book id does not exist       |
| 500    | Internal Server Error — unexpected error |

## Project layout

```
src/
  lib.rs    # domain logic, handlers, router
  main.rs   # binary entrypoint (binds server, adds tracing layer)
  tests.rs  # unit + integration tests
Cargo.toml
README.md
```

## Tests

```bash
cargo test
```

The suite covers:

- Create + get book flow
- Input validation (empty title/author rejected)
- List filtering by author
- Update then delete lifecycle
- 404 on missing book
- Full HTTP integration test through axum's `Router` (health, create, list, validation)
- `open_connection` initializes the schema

## Running offline

All dependencies are pinned to versions available in the local cargo cache, so
the project builds and tests fully offline:

```bash
cargo build --offline
cargo test --offline
```
