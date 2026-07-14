# Book Collection API

A small REST API for managing a book collection, built with **TypeScript + Express +
better-sqlite3**, with a Vitest integration test suite.

## Endpoints

| Method | Path            | Description                                            |
| ------ | --------------- | ------------------------------------------------------ |
| GET    | `/health`       | Liveness probe — returns `{ "status": "ok" }`          |
| POST   | `/books`        | Create a book (`title`, `author` required)             |
| GET    | `/books`        | List books. Optional filter: `?author=Name`            |
| GET    | `/books/{id}`   | Fetch a single book by numeric ID                      |
| PUT    | `/books/{id}`   | Update an existing book (partial — at least one field) |
| DELETE | `/books/{id}`   | Delete a book. Returns `204 No Content` on success     |

### Book shape

```json
{
  "id": 1,
  "title": "The Pragmatic Programmer",
  "author": "Andrew Hunt",
  "year": 1999,
  "isbn": "978-0201616224",
  "createdAt": "2026-06-13 16:31:19",
  "updatedAt": "2026-06-13 16:31:19"
}
```

`year` and `isbn` are optional and stored as `null` when not provided. The other
two fields are trimmed and required.

### Status codes

| Code | When |
| ---- | ---- |
| 200  | Read / update success |
| 201  | Book created |
| 204  | Book deleted |
| 400  | Invalid JSON body, validation error, or non-numeric ID |
| 404  | Book not found (or unknown route) |
| 500  | Unhandled server error |

Validation errors include a `details` array, e.g.:

```json
{ "error": "Validation failed: author is required and must be a string",
  "details": ["author is required and must be a string"] }
```

## Requirements

- Node.js ≥ 20 (uses native `node:test`-style ESM resolution)
- A working C toolchain is **not** required — `better-sqlite3` ships prebuilt
  binaries for macOS arm64 / x64, Linux glibc / musl, and Windows.

## Install

```sh
npm install
```

## Run (production)

```sh
npm run build
npm start
```

`npm start` honors two env vars:

| Var      | Default     | Meaning                                  |
| -------- | ----------- | ---------------------------------------- |
| `PORT`   | `3000`      | TCP port to listen on                    |
| `DB_PATH`| `books.db`  | SQLite file path (use `:memory:` for in-memory) |

The server creates `books.db` next to the project on first start.

## Run (development, auto-reload not included)

```sh
npm run dev
```

This runs `tsx src/server.ts` directly, no watch.

## Test

```sh
npm test
```

Tests use `supertest` against an in-memory SQLite instance and cover:

- Health endpoint
- Create with all fields, missing `title`, missing `author`, whitespace-only
  `title`
- List (empty, all, filtered by author)
- Get (found, not found, non-numeric id)
- Update (success, clearing optional fields, missing book, empty body)
- Delete (success, missing)
- Error paths (unknown route, malformed JSON)

## Project layout

```
src/
  app.ts          Express app factory + global error middleware
  server.ts       Entry point: opens DB, mounts routes, listens
  db.ts           SQLite schema + BookRepository
  validation.ts   Input parsing for create / update payloads
  routes/
    books.ts      /books router (CRUD)
    health.ts     /health router
test/
  books.test.ts   Integration tests
  helpers.ts      App builder + supertest wrappers
```

## Notes

- Storage is local SQLite via `better-sqlite3` — single-file, zero-config, fast.
- The repository module is a typed seam: `createRepository(db)` returns
  `BookRepository`, and `createApp({ repository })` consumes it. Tests use this
  seam to inject an in-memory DB.
- All timestamps are stored as UTC `datetime('now')` strings.
