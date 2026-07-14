# Books API

A small REST API for managing a book collection, written in **TypeScript** with **Express**, **SQLite** (`better-sqlite3`), and **Zod** for input validation. Tests run on **Vitest** using `supertest`.

## Endpoints

| Method | Path            | Description                                                    |
| ------ | --------------- | ------------------------------------------------------------- |
| GET    | `/health`       | Health check -> `{"status":"ok"}` (200)                       |
| POST   | `/books`        | Create a book. Body: `{title, author, year?, isbn?}` (201)    |
| GET    | `/books`        | List all books. Supports `?author=<name>` filter (200)        |
| GET    | `/books/{id}`   | Get a single book (200 / 404)                                  |
| PUT    | `/books/{id}`   | Update a book. Body: any subset of the create fields (200)    |
| DELETE | `/books/{id}`   | Delete a book (204 / 404)                                      |

`title` and `author` are required on create. `year` (0–9999) and `isbn` (≤50 chars) are optional. All responses are JSON (DELETE has an empty body).

## Prerequisites

- Node.js 18+ (tested on Node 22)
- npm 9+

## Setup

```bash
npm install
npm run build
```

## Run

```bash
# Production-style (compiled JS in dist/)
npm start
# defaults: port 3000, SQLite file at data/books.sqlite

# Override via env:
PORT=4000 DB_FILE=./my.db npm start

# Development with auto-reload (no build needed)
npm run dev
```

The SQLite file is created automatically on first run (the `data/` directory is created too).

## Tests

```bash
npm test
```

Tests use an in-memory SQLite database (one fresh DB per test), so they don't touch the on-disk file. There are integration tests covering:

- the health endpoint
- create + read + list + filter
- input validation (missing required fields, unknown fields, empty update body)
- 404s and 400s for bad IDs
- update preserving untouched fields
- delete semantics

## Project layout

```
src/
  db.ts                 SQLite open/migrate/close helpers
  validation.ts         Zod schemas for create/update
  books.repository.ts   Data-access layer
  books.routes.ts       Express router for /books
  app.ts                Express app composition (health + /books + error handlers)
  server.ts             Listens on a port, opens the DB file, handles SIGINT/SIGTERM
tests/
  books.test.ts         Vitest + supertest integration tests
tsconfig.json
vitest.config.ts
package.json
README.md
```

## Example session

```bash
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Clean Code","author":"Robert C. Martin","year":2008,"isbn":"9780132350884"}'

curl http://localhost:3000/books
curl 'http://localhost:3000/books?author=Robert%20C.%20Martin'
curl http://localhost:3000/books/1
curl -X PUT http://localhost:3000/books/1 -H 'Content-Type: application/json' -d '{"year":2009}'
curl -X DELETE http://localhost:3000/books/1
curl http://localhost:3000/health
```
