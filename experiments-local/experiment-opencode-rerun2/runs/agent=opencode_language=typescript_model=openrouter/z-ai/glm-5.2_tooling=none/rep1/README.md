# Books API

A REST API service for managing a book collection, written in TypeScript with Express and SQLite (`better-sqlite3`).

## Endpoints

| Method   | Path           | Description                                  |
| -------- | -------------- | -------------------------------------------- |
| `GET`    | `/health`      | Health check                                 |
| `POST`   | `/books`       | Create a new book (title, author, year, isbn)|
| `GET`    | `/books`       | List all books; supports `?author=` filter  |
| `GET`    | `/books/{id}`  | Get a single book                            |
| `PUT`    | `/books/{id}`  | Update a book (partial update supported)     |
| `DELETE` | `/books/{id}`  | Delete a book (returns `204 No Content`)    |

### Validation rules
- `title` and `author` are required on create (non-empty strings).
- `year` (integer 0–9999) and `isbn` (string) are optional; stored as `null` if omitted.
- `PUT` accepts a partial body but requires at least one updatable field.

### Status codes
- `200` — successful read / update / list
- `201` — successful create
- `204` — successful delete
- `400` — validation failure or invalid id
- `404` — book not found (or unknown route)

## Setup

```bash
npm install
npm run build
```

## Run

```bash
npm start                  # uses ./books.db and port 3000
# or override via env:
DB_PATH=/tmp/books.db PORT=8080 npm start
# or live-reload during development:
npm run dev
```

The SQLite database file is created automatically on first run.

## Test

```bash
npm test                   # runs the vitest suite
npm run test:watch         # watch mode
```

Tests are integration tests using `supertest` against an in-memory SQLite database. They cover:

1. Health check, create + list + filter + get by id + 404 paths.
2. Validation failures (missing title / missing author / empty update body / invalid id).
3. Update (partial merge) and delete (204 + subsequent 404).

## Project layout

```
src/
  server.ts          # express app + server bootstrap
  db.ts              # SQLite open + CRUD helpers
  validation.ts     # zod schemas and error formatting
  types.ts           # shared types
  routes/
    books.ts         # /books router
    health.ts        # /health router
tests/
  books.test.ts
```
