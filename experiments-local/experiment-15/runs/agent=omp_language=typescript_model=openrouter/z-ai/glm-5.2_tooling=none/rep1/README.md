# Book Collection API

A REST API service for managing a book collection, written in TypeScript with
Express and SQLite (`better-sqlite3`).

## Endpoints

| Method   | Path          | Description                                  |
| -------- | ------------- | -------------------------------------------- |
| `GET`    | `/health`     | Health check (`{ "status": "ok" }`).        |
| `POST`   | `/books`       | Create a book. Returns `201` + the book.   |
| `GET`    | `/books`        | List all books. Supports `?author=` filter. |
| `GET`    | `/books/{id}`   | Get a single book. `404` if not found.     |
| `PUT`    | `/books/{id}`   | Partially update a book.                  |
| `DELETE` | `/books/{id}`   | Delete a book. Returns `204` on success.    |

### Book shape

```json
{ "id": 1, "title": "...", "author": "...", "year": 1999, "isbn": "..." }
```

`title` and `author` are required (non-empty strings). `year` (non-negative
integer) and `isbn` (string) are optional. `PUT` accepts any subset of these
fields and merges with the stored book.

## Setup

```bash
npm install
npm run build
```

## Run

```bash
npm start
# or run directly from TS:
npm run dev
```

By default the server listens on `http://localhost:3000` and stores data in
`books.db` (SQLite) in the working directory. Override with environment
variables:

```bash
PORT=4000 DB_PATH=/tmp/books.db npm start
```

## Example

```bash
curl -s -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Pragmatic Programmer","author":"Andrew Hunt","year":1999,"isbn":"978-0201616224"}'

curl -s 'http://localhost:3000/books?author=Andrew%20Hunt'
```

## Tests

```bash
npm test
```

Tests are integration tests that exercise the real Express app against a fresh
in-memory SQLite database for each case (no file I/O, no external services).

## Project layout

```
src/
  db.ts          SQLite setup + table creation
  validation.ts  create/update input validation
  books.ts       Express router with book CRUD routes
  server.ts      App factory + server entrypoint
tests/
  books.test.ts  End-to-end tests via supertest
```
