# book-api

A REST API for managing a book collection, built with **TypeScript**, **[Hono](https://hono.dev)** (web framework), and **SQLite** via [`better-sqlite3`](https://github.com/WiseLibs/better-sqlite3).

## Endpoints

| Method | Path              | Description                          | Status codes          |
| ------ | ----------------- | ------------------------------------ | --------------------- |
| GET    | `/health`         | Health check                         | 200                   |
| POST   | `/books`           | Create a book (title, author, year, isbn) | 201, 400         |
| GET    | `/books`           | List books (`?author=` filter supported)  | 200             |
| GET    | `/books/{id}`     | Get a single book by ID              | 200, 404              |
| PUT    | `/books/{id}`     | Partially update a book              | 200, 400, 404        |
| DELETE | `/books/{id}`     | Delete a book                         | 204, 404           |

### Validation rules

- `title` and `author` are **required** on create and must be non-empty strings.
- `year` (if provided) must be an integer between 0 and 9999 (or `null`).
- `isbn` (if provided) must be a string (or `null`).
- On update (`PUT`), any provided field follows the same per-field rules; at least one field must be provided.

## Setup

Requirements: **Node.js >= 20** and npm.

```bash
npm install
```

## Run

```bash
# development (hot reload via tsx)
npm run dev

# production-style
npm run build
npm start
```

By default the server listens on `http://localhost:3000` and stores data in `./books.db`. Override with env vars:

```bash
PORT=4000 DB_PATH=/tmp/books.db npm run dev
```

## Test

```bash
npm test
```

Tests use `vitest` with an in-memory SQLite database (no file artifacts, no network). Coverage includes health, create + validation, list + filter, get-by-id, update, and delete flows.

## Project layout

```
src/
  app.ts        # Hono routes wired to a database
  books.ts       # Book domain types and repository functions
  db.ts          # SQLite open/close + schema migration
  validate.ts    # Input validation (named result types)
  server.ts      # Node server entrypoint
test/
  books.test.ts # Integration tests
```
