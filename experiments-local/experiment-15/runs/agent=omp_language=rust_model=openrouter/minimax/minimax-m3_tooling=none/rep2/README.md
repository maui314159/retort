# book-collection-api

A small REST API for managing a book collection. Books are stored in a
local SQLite file. Written in Rust on top of [Axum] 0.7 and [SQLx] 0.8.

[Axum]: https://github.com/tokio-rs/axum
[SQLx]: https://github.com/launchbadge/sqlx

## Endpoints

| Method | Path             | Description                              | Success | Errors         |
|--------|------------------|------------------------------------------|---------|----------------|
| GET    | `/health`        | Liveness probe                           | 200     | —              |
| POST   | `/books`         | Create a book                            | 201     | 400            |
| GET    | `/books`         | List books (`?author=` substring filter) | 200     | —              |
| GET    | `/books/:id`     | Fetch one book                           | 200     | 404            |
| PUT    | `/books/:id`     | Replace a book                           | 200     | 400, 404       |
| DELETE | `/books/:id`     | Remove a book                            | 204     | 404            |

### Book payload

```json
{
  "title": "The Left Hand of Darkness",
  "author": "Ursula K. Le Guin",
  "year": 1969,
  "isbn": "978-0-441-17271-9"
}
```

- `title` (string, required, ≤ 500 chars) — non-empty after trim.
- `author` (string, required, ≤ 200 chars) — non-empty after trim.
- `year` (integer, optional) — must be in `1..=9999` if provided.
- `isbn` (string, optional, ≤ 32 chars) — an empty string is treated as `null`.

Stored books also carry server-managed `id`, `created_at`, and `updated_at`
fields, which are returned with every response.

### Error responses

Errors are JSON of the shape `{"error": {"code": "...", "message": "..."}}`:

```json
{ "error": { "code": "validation_error", "message": "validation error: 'title' is required" } }
```

Codes:

- `validation_error` (400) — missing or malformed field.
- `not_found` (404) — no book with that `id`.
- `bad_request` (400) — unparseable path or query parameter.
- `internal_error` (500) — database or other server failure.

## Requirements

- Rust **1.75** or newer (tested with 1.95).
- No system-level database dependencies — SQLite is bundled via the
  `rusqlite`-bundled feature inside `sqlx`.

## Setup

Clone the repository and fetch the dependencies:

```sh
cargo fetch
```

That's it — there is no separate `migrate` step. The schema is applied
automatically when the server starts (and by the integration tests when
they boot their test databases).

## Run

```sh
cargo run --release
```

The server binds to `0.0.0.0:8080` by default and creates `books.db` in
the current working directory if it doesn't already exist. Override either
of these with environment variables:

| Variable        | Default                              | Notes                                      |
|-----------------|--------------------------------------|--------------------------------------------|
| `BIND_ADDR`     | `0.0.0.0:8080`                       | Any `SocketAddr` (e.g. `127.0.0.1:9000`).  |
| `DATABASE_URL`  | `sqlite://books.db?mode=rwc`         | Standard `sqlx` SQLite connection string.  |
| `RUST_LOG`      | `info,book_collection_api=debug`     | Standard `tracing` env-filter syntax.      |

For example, to run on a different port against an in-memory database:

```sh
DATABASE_URL="sqlite::memory:" BIND_ADDR="127.0.0.1:9000" cargo run --release
```

## Try it

```sh
# Health
curl -s http://127.0.0.1:8080/health

# Create
curl -s -X POST http://127.0.0.1:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

# List (filter by author)
curl -s 'http://127.0.0.1:8080/books?author=Herbert'

# Get one
curl -s http://127.0.0.1:8080/books/1

# Update
curl -s -X PUT http://127.0.0.1:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune (Revised)","author":"Frank Herbert","year":1965}'

# Delete
curl -s -X DELETE http://127.0.0.1:8080/books/1 -i
```

## Tests

```sh
cargo test
```

The test suite includes:

- **Unit tests** in `src/model.rs` covering validation rules
  (required fields, blank strings, length bounds, year range).
- **Integration tests** in `tests/integration.rs` that boot the real
  router against a temporary SQLite file and exercise it over HTTP via
  `reqwest`. The integration suite covers the full create → read →
  list → update → delete lifecycle, the `?author=` filter, validation
  errors, `404` for unknown ids, and `400` for unparseable path
  parameters.

## Project layout

```
.
├── Cargo.toml
├── README.md
├── src
│   ├── main.rs        # binary entry point — configures tracing, opens pool, serves
│   ├── lib.rs         # library entry point — re-exports public modules
│   ├── db.rs          # SQLite pool & schema
│   ├── error.rs       # AppError + IntoResponse mapping to HTTP status codes
│   ├── model.rs       # Book / BookCreate / BookUpdate + validation
│   ├── handlers.rs    # HTTP handlers (create/list/get/update/delete/health)
│   └── router.rs      # Router::new() construction shared by binary and tests
└── tests
    └── integration.rs # end-to-end HTTP tests
```

## Design notes

- **State is a single `Pool<Sqlite>`** cloned into the router. Handlers
  take a `State<AppState>` extractor.
- **Validation happens before any I/O.** `BookCreate::validate()` and
  `BookUpdate::validate()` trim strings, enforce non-emptiness and
  length bounds, and return a `400 validation_error` response on
  failure. The handlers never see an invalid payload.
- **Errors map to HTTP via `IntoResponse`.** `AppError` is the single
  error type returned by handlers; `Validation` and `BadRequest`
  become `400`, `NotFound` becomes `404`, and database / unknown
  failures become `500`.
- **Schema is idempotent.** `CREATE TABLE IF NOT EXISTS` and
  `CREATE INDEX IF NOT EXISTS` mean it's safe to run on every startup.
- **`PUT` is a full replacement**, not a partial update. `title` and
  `author` are required; `year` and `isbn` are accepted (and may be
  `null` to clear).
