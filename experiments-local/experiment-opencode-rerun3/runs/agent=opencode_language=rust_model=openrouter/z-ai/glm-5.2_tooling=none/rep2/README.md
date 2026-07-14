# Books API

A small REST API for managing a book collection, written in Rust using
[`axum`](https://crates.io/crates/axum) + [`rusqlite`](https://crates.io/crates/rusqlite)
(SQLite) + `tokio`.

## Endpoints

| Method  | Path          | Description                          |
|---------|---------------|--------------------------------------|
| GET     | `/health`     | Health check                         |
| POST    | `/books`      | Create a book                        |
| GET     | `/books`      | List books (optional `?author=`)     |
| GET     | `/books/{id}` | Get a single book                    |
| PUT     | `/books/{id}` | Update a book (partial/PUT supported)|
| DELETE  | `/books/{id}` | Delete a book                        |

### Book shape

```json
{ "id": 1, "title": "The Hobbit", "author": "Tolkien", "year": 1937, "isbn": "..." }
```

`title` and `author` are required and validated to be non-empty on create.
On update, any provided field replaces the existing value, and `title`/`author`
are rejected if provided as empty strings.

### Status codes

- `200 OK` — successful GET / PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — validation error (JSON `{ "error": "..." }`)
- `404 Not Found` — book id does not exist
- `500 Internal Server Error` — unexpected DB error

## Setup & run

Requires the Rust toolchain (`cargo` 1.74+).

```bash
cargo run --release
```

The server listens on `0.0.0.0:3000`. The SQLite database file defaults to
`books.db` in the working directory; override with the `DB_PATH` environment
variable:

```bash
DB_PATH=/var/lib/books.db cargo run --release
```

### Examples

```bash
# Create
curl -s localhost:3000/books -H 'content-type: application/json' \
  -d '{"title":"The Hobbit","author":"Tolkien","year":1937,"isbn":"9780261103283"}'

# List all
curl -s localhost:3000/books

# List filtered by author
curl -s 'localhost:3000/books?author=Tolkien'

# Get one
curl -s localhost:3000/books/1

# Update
curl -s -X PUT localhost:3000/books/1 -H 'content-type: application/json' \
  -d '{"year":1938}'

# Delete
curl -s -X DELETE localhost:3000/books/1
```

## Tests

```bash
cargo test
```

The suite (`tests/api.rs`) spins up an in-memory SQLite database and exercises
the router directly via `tower::ServiceExt::oneshot`, covering:

- creating and fetching a book (201 + GET 200)
- rejecting an empty `title` on create (400)
- listing with the `?author=` filter, deleting, and confirming 404 afterwards
- partial update via PUT
- the `/health` endpoint

## Layout

```
src/main.rs     # all handlers, DB access, router, server entrypoint
tests/api.rs    # integration tests
Cargo.toml
```
