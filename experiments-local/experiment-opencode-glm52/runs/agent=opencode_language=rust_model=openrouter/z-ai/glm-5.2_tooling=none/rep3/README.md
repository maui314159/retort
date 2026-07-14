# Book API

A REST API for managing a book collection, written in Rust using [axum](https://github.com/tokio-rs/axum) and [sqlx](https://github.com/launchbadge/sqly) with an embedded SQLite database.

## Endpoints

| Method   | Path           | Description                          |
|----------|----------------|--------------------------------------|
| `GET`    | `/health`      | Health check                         |
| `POST`   | `/books`       | Create a book                        |
| `GET`    | `/books`       | List books (supports `?author=`)     |
| `GET`    | `/books/{id}`  | Get a single book                    |
| `PUT`    | `/books/{id}`  | Update a book (partial supported)    |
| `DELETE` | `/books/{id}`  | Delete a book                        |

### Book shape

```json
{
  "id": 1,
  "title": "The Rust Book",
  "author": "Steve Klabnik",
  "year": 2019,
  "isbn": "9781593278282"
}
```

`title` and `author` are required on create; `year` and `isbn` are optional. On
`PUT`, any field may be omitted (only provided fields are updated; providing an
empty string for `title`/`author` returns `400`).

## Setup

Requires a recent Rust toolchain (1.74+):

```bash
cargo build
```

## Run

```bash
cargo run
```

The server listens on `0.0.0.0:3000` by default. Override with:

```bash
LISTEN_ADDR=127.0.0.1:8080 cargo run
```

The SQLite database file defaults to `books.db` in the working directory.
Override with `DATABASE_URL=sqlite:path/to/file.db`.

## Tests

```bash
cargo test
```

Includes unit/integration tests covering: health check, create + get flow,
input validation, author filtering, and update + delete lifecycle.

## Example

```bash
curl -sX POST localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Foo","author":"Bar","year":2020}'

curl -s 'localhost:3000/books?author=Bar'
```
