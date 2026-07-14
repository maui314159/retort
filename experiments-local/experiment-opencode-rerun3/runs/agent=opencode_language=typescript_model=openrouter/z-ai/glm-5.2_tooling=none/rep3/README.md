# Book Collection API

A small REST API service for managing a book collection, written in TypeScript
with Express and Node's built-in SQLite (`node:sqlite`).

## Requirements

- Node.js 22+ (`node:sqlite` is an experimental built-in module, so a recent
  Node is required)

## Setup

```bash
npm install
npm run build      # type-check and compile to dist/
```

## Run

```bash
# Run the compiled build (uses ./books.db for storage by default)
npm start

# Or run directly from TypeScript sources with tsx
npm run dev

# Override port and database path via environment
PORT=4000 DB_PATH=/tmp/books.db npm start
```

The server listens on `http://localhost:3000` by default.

## Endpoints

| Method   | Path            | Description                                  |
|---------|-----------------|----------------------------------------------|
| GET     | `/health`       | Health check                                 |
| POST    | `/books`        | Create a book (`title`, `author` required;  |
|         |                 | optional `year`, `isbn`)                     |
| GET     | `/books`        | List books; supports `?author=` filter       |
| GET     | `/books/{id}`   | Get a single book                            |
| PUT     | `/books/{id}`   | Update a book (partial updates supported)    |
| DELETE  | `/books/{id}`   | Delete a book (204 No Content on success)    |

## Tests

```bash
npm test
npm run typecheck   # tsc --noEmit
```

Tests use Vitest and `supertest` against an in-memory SQLite database per
test, exercising CRUD operations, validation, filtering, and error cases.

## Project Layout

```
src/
  db.ts        # SQLite setup, validation, CRUD helpers
  server.ts     # Express app factory + entrypoint
tests/
  books.test.ts # integration tests
```
