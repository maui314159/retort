# Books API

A REST API service for managing a book collection, built with **TypeScript**, **Express**, **SQLite** (via `better-sqlite3`), and **Zod** for input validation.

## Requirements

- Node.js 18+ (tested on Node 22)
- npm

## Setup

```bash
npm install
npm run build
```

## Running

```bash
# Production (compiled)
npm start

# Development (tsx, no build step)
npm run dev
```

By default the server listens on `http://localhost:3000` and uses an in-memory
database. To persist data to a file, set the `DB_PATH` environment variable:

```bash
DB_PATH=./books.db PORT=8080 npm start
```

## Endpoints

| Method | Path           | Description                          |
|--------|----------------|--------------------------------------|
| GET    | `/health`      | Health check                         |
| POST   | `/books`       | Create a book                        |
| GET    | `/books`       | List books (supports `?author=`)     |
| GET    | `/books/{id}`  | Get a single book                    |
| PUT    | `/books/{id}`  | Update a book (partial allowed)      |
| DELETE | `/books/{id}`  | Delete a book                        |

### Book shape

```json
{
  "id": 1,
  "title": "The Pragmatic Programmer",
  "author": "Andrew Hunt",
  "year": 1999,
  "isbn": "978-0201616224"
}
```

`title` and `author` are required. `year` and `isbn` are optional.

### Example

```bash
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Pragmatic Programmer","author":"Andrew Hunt","year":1999,"isbn":"978-0201616224"}'
```

## Status codes

- `200` — success (GET, PUT)
- `201` — created (POST)
- `204` — no content (DELETE)
- `400` — validation error / invalid JSON
- `404` — book or route not found
- `500` — internal server error

## Tests

Tests use `vitest` and `supertest` against an in-memory database.

```bash
npm test
```

## Project layout

```
src/
  db.ts          SQLite connection + schema
  validation.ts  Zod schemas for book input
  books.ts       /books router with CRUD handlers
  server.ts      Express app factory + entrypoint
tests/
  books.test.ts  Integration tests
```
