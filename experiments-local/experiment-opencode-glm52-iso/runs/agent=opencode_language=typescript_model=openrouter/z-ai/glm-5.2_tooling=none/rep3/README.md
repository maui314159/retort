# Book Collection API

A REST API service for managing a book collection, written in TypeScript with Express and SQLite (via `better-sqlite3`).

## Requirements

- Node.js 18+ (tested on Node 22)
- npm

## Setup

```bash
npm install
```

## Build

```bash
npm run build
```

Compiled output is written to `dist/`.

## Run

```bash
# Production (built)
npm start

# Development
npm run dev
```

By default the server listens on `http://localhost:3000` and stores data in `./books.db`.

### Configuration (environment variables)

| Variable | Default      | Description                          |
| -------- | ------------ | ------------------------------------ |
| `PORT`   | `3000`       | HTTP port the API listens on.         |
| `DB_PATH`| `books.db`   | Path to the SQLite database file.    |

## Endpoints

| Method   | Path           | Description                                   |
| -------- | -------------- | --------------------------------------------- |
| `GET`    | `/health`       | Health check; returns `{ "status": "ok" }`.   |
| `POST`   | `/books`        | Create a new book.                             |
| `GET`    | `/books`         | List all books; supports `?author=` filter.   |
| `GET`    | `/books/{id}`    | Get a single book by ID.                       |
| `PUT`    | `/books/{id}`    | Update a book.                                 |
| `DELETE` | `/books/{id}`     | Delete a book (returns `204 No Content`).       |

### Book shape

```json
{
  "id": 1,
  "title": "The Pragmatic Programmer",
  "author": "Hunt & Thomas",
  "year": 1999,
  "isbn": "9780201616224"
}
```

### Validation

- `title` and `author` are required and must be non-empty strings.
- `year`, if provided, must be an integer (or `null`).
- `isbn`, if provided, must be a string (or `null`).

### Status codes

| Code | Meaning                                   |
| ---- | ----------------------------------------- |
| 200  | OK (GET, PUT)                             |
| 201  | Created (POST)                            |
| 204  | No Content (DELETE)                       |
| 400  | Bad Request (validation error, bad id)    |
| 404  | Not Found (unknown book id)               |
| 500  | Internal Server Error (unexpected failure) |

## Tests

```bash
npm test
```

Tests use Jest and Supertest against an in-memory test SQLite database (one fresh DB per test). At least 3 test suites cover:

- `tests/api.test.ts` — integration tests for every endpoint, including validation, `?author=` filtering, status codes, and the health check.
- `tests/store.test.ts` — unit tests for the `BookStore` data-access layer.

## Project layout

```
src/
  index.ts   # entrypoint: starts the Express server
  app.ts     # routes, validation, error handling
  store.ts   # SQLite-backed BookStore data-access layer
tests/
  api.test.ts
  store.test.ts
```

## Example usage

```bash
# Create a book
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Pragmatic Programmer","author":"Hunt & Thomas","year":1999,"isbn":"9780201616224"}'

# List books by author
curl "http://localhost:3000/books?author=Hunt%20%26%20Thomas"

# Get a single book
curl http://localhost:3000/books/1

# Update a book
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"New Title","author":"New Author","year":2020}'

# Delete a book
curl -X DELETE http://localhost:3000/books/1 -i
```
