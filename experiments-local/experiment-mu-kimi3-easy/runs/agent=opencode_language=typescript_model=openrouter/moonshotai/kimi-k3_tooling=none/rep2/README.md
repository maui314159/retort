# Book Collection API

A REST API service for managing a book collection, written in TypeScript with
Express and SQLite (via `better-sqlite3`).

## Endpoints

| Method   | Path          | Description                                  |
| -------- | ------------- | -------------------------------------------- |
| `GET`    | `/health`     | Health check — returns `{"status": "ok"}`    |
| `POST`   | `/books`      | Create a book (`title`, `author` required; `year`, `isbn` optional) |
| `GET`    | `/books`      | List all books; supports `?author=` filter   |
| `GET`    | `/books/{id}` | Get a single book by ID                      |
| `PUT`    | `/books/{id}` | Update a book (full replacement of fields)   |
| `DELETE` | `/books/{id}` | Delete a book                                |

Responses are JSON with appropriate HTTP status codes:
`201` created, `200` success, `204` deleted, `400` validation error,
`404` not found.

## Setup

```sh
npm install
```

Requires Node.js 18+ (developed against Node 22).

## Run

```sh
npm run build   # compile TypeScript to dist/
npm start       # serve on http://localhost:3000
```

Development mode (no build step):

```sh
npm run dev
```

Configuration via environment variables:

- `PORT` — listen port (default `3000`)
- `DB_PATH` — SQLite database file (default `books.db`; use `:memory:` for
  an ephemeral in-memory database)

## Test

```sh
npm test
```

Integration tests spin up the app against an in-memory SQLite database on an
ephemeral port and exercise all endpoints (health, create, validation errors,
list + author filter, get/update/delete, 404/400 handling).

## Example

```sh
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-441-17271-9"}'

curl 'http://localhost:3000/books?author=Frank%20Herbert'
```

## Project layout

```
src/
  types.ts   — Book / BookInput types
  db.ts      — SQLite persistence layer (BookStore)
  app.ts     — Express app factory: routes + validation
  server.ts  — entrypoint (PORT, DB_PATH, graceful shutdown)
tests/
  books.test.ts — integration tests (node:test + fetch)
```
