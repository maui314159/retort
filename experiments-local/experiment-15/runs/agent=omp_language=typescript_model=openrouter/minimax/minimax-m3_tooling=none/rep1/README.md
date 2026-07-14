# Book Collection API

A small REST API for managing a book collection, built with TypeScript, Express, and SQLite (via `better-sqlite3`).

## Requirements

- Node.js **22.5.0 or newer** (`better-sqlite3` ships with prebuilt binaries; no native compile required on supported platforms).

## Install

```bash
npm install
```

## Build

```bash
npm run build
```

This compiles `src/**` into `dist/`.

## Run

```bash
npm start
```

Configuration is via environment variables:

| Variable | Default       | Description                                |
|----------|---------------|--------------------------------------------|
| `PORT`   | `3000`        | TCP port the HTTP server binds to.         |
| `HOST`   | `127.0.0.1`   | Interface to bind.                         |
| `DB_PATH`| `books.db`    | SQLite file path. Use `:memory:` for RAM.  |

The server creates the SQLite schema automatically on first run.

## Test

```bash
npm test
```

12 integration tests run against an in-memory database with no live network port required.

## API

All request and response bodies are JSON. Book records have the shape:

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441172719"
}
```

`year` and `isbn` are optional; they are `null` when not set.

### `GET /health`

Health check. Always returns `200 { "status": "ok" }`.

### `POST /books`

Create a book. Body must include non-empty `title` and `author`. `year` (number) and `isbn` (string) are optional.

- `201` with the created book.
- `400` with `{ "error": "validation_failed", "details": [...] }` if validation fails.

### `GET /books`

List all books. Accepts an optional `?author=<substring>` query parameter for case-insensitive substring filtering.

- `200` with an array of books (possibly empty).

### `GET /books/{id}`

Fetch a single book.

- `200` with the book.
- `400` if `id` is not a positive integer.
- `404` if no book has that id.

### `PUT /books/{id}`

Replace a book's fields. Body must include non-empty `title` and `author`.

- `200` with the updated book.
- `400` on invalid id or validation failure.
- `404` if no book has that id.

### `DELETE /books/{id}`

Delete a book.

- `204` on success.
- `400` on invalid id.
- `404` if no book has that id.

## Example session

```bash
curl -X POST http://127.0.0.1:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

curl "http://127.0.0.1:3000/books?author=frank"
curl http://127.0.0.1:3000/books/1
curl -X PUT http://127.0.0.1:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune (2nd ed)","author":"Frank Herbert","year":1966,"isbn":"9780441172719"}'
curl -X DELETE http://127.0.0.1:3000/books/1
```

## Project layout

```
src/
  app.ts         Express app factory (no listen); testable
  server.ts      Process entry point; calls app.listen
  db.ts          SQLite store wrapper (better-sqlite3)
  validation.ts  Request body and id parsing
tests/
  books.test.ts  Supertest integration tests
```

## Notes

- Author filtering is a case-insensitive **substring** match. Wildcard characters (`%`, `_`) in the query string are escaped and treated as literals.
- The default `DB_PATH` (`books.db`) is created in the working directory. Delete it to start with an empty store.
