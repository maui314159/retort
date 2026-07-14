# Books API

A REST API service for managing a book collection, written in Rust using
[`axum`](https://docs.rs/axum) for the web framework and
[`rusqlite`](https://docs.rs/rusqlite) for an embedded SQLite database.

## Endpoints

| Method   | Path             | Description                                  |
|---------|------------------|----------------------------------------------|
| `GET`   | `/health`        | Health check                                 |
| `POST`   | `/books`         | Create a new book                            |
| `GET`   | `/books`         | List all books (supports `?author=` filter)  |
| `GET`   | `/books/{id}`    | Get a single book by ID                      |
| `PUT`   | `/books/{id}`    | Update a book (partial update supported)     |
| `DELETE` | `/books/{id}`    | Delete a book                                |

### Book JSON shape

```json
{
  "id": 1,
  "title": "The Hobbit",
  "author": "Tolkien",
  "year": 1937,
  "isbn": "123"
}
```

`title` and `author` are required and must be non-empty. `year` and `isbn`
are optional.

## Status codes

| Code | Meaning                                  |
|------|------------------------------------------|
| 200  | OK (read/update)                         |
| 201  | Created                                  |
| 204  | No content (delete)                      |
| 400  | Bad request (validation failure)        |
| 404  | Not found                                |
| 500  | Internal server error (database failure) |

## Setup

Requires the Rust toolchain (`rustc` + `cargo`). No external database is
needed — SQLite is embedded via the `bundled` feature of `rusqlite`, which
compiles SQLite from source.

```bash
cargo build
```

## Run

```bash
cargo run
# server listens on 0.0.0.0:8080
```

The database is an in-memory SQLite instance initialized at startup.

## Examples

```bash
# Create a book
curl -X POST http://localhost:8080/books \
  -H 'content-type: application/json' \
  -d '{"title":"The Hobbit","author":"Tolkien","year":1937,"isbn":"123"}'

# List all books
curl http://localhost:8080/books

# Filter by author
curl 'http://localhost:8080/books?author=Tolkien'

# Get a book
curl http://localhost:8080/books/1

# Update a book (partial)
curl -X PUT http://localhost:8080/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"The Hobbit (Revised)"}'

# Delete a book
curl -X DELETE http://localhost:8080/books/1

# Health check
curl http://localhost:8080/health
```

## Tests

The integration tests build the application router with an isolated
in-memory database and exercise it via `tower::ServiceExt::oneshot`
(no network binding required).

```bash
cargo test
```

Test cases:

- `create_get_and_delete_book` — full CRUD lifecycle with status checks
- `validation_rejects_empty_title` — empty `title` returns `400`
- `list_books_with_author_filter` — `?author=` filter and unfiltered list
- `update_book_fields` — partial update preserves untouched fields
- `health_check_ok` — `/health` returns `200` with `{"status":"ok"}`

A unit-level validation test for `CreateBook::validate` lives in
`src/models.rs`:

```bash
cargo test --lib
```
