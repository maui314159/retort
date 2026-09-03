# Book Collection API

A REST API service for managing a book collection, built with **TypeScript**, **Express**, and **SQLite** (`better-sqlite3`).

## Endpoints

| Method  | Path            | Description                                  |
|---------|-----------------|----------------------------------------------|
| GET     | `/health`       | Health check                                 |
| POST    | `/books`        | Create a new book                            |
| GET     | `/books`        | List all books (supports `?author=` filter)  |
| GET     | `/books/:id`    | Get a single book by ID                      |
| PUT     | `/books/:id`    | Update a book                                |
| DELETE  | `/books/:id`    | Delete a book                                |

### Book fields

```json
{
  "id": 1,
  "title": "The Hobbit",
  "author": "J.R.R. Tolkien",
  "year": 1937,
  "isbn": "9780261102217"
}
```

- `title` and `author` are **required** and must be non-empty strings.
- `year` is optional (integer or `null`).
- `isbn` is optional (string or `null`).

Responses are wrapped in a `{ "data": ... }` envelope, with appropriate HTTP status codes (`200`, `201`, `204`, `400`, `404`, `500`).

## Prerequisites

- Node.js 18+ (developed on Node 22)
- npm

## Setup

```bash
# install dependencies
npm install

# compile TypeScript
npm run build
```

## Running

```bash
# Start the server (reads dist/src/server.js)
npm start

# Or run directly from source without compiling
npm run dev
```

By default the server listens on `http://localhost:3000` and stores books in a local `books.db` SQLite file. Override with environment variables:

```bash
PORT=4000 DB_PATH=/tmp/books.db npm start
```

## Usage examples

```bash
# Health check
curl http://localhost:3000/health

# Create a book
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937,"isbn":"9780261102217"}'

# List all books
curl http://localhost:3000/books

# List books by author
curl 'http://localhost:3000/books?author=Alice'

# Get / update / delete by id
curl http://localhost:3000/books/1
curl -X PUT http://localhost:3000/books/1 -H 'Content-Type: application/json' -d '{"title":"New","author":"New","year":2020}'
curl -X DELETE http://localhost:3000/books/1
```

## Project layout

```
src/
  types.ts   # shared TypeScript interfaces
  db.ts      # SQLite (better-sqlite3) data access layer
  app.ts     # Express app factory with routes + validation
  server.ts  # entry point that starts the HTTP server
tests/
  books.test.ts # integration tests (node:test + supertest)
```

## Testing

```bash
npm run build
npm test
```

The test suite uses Node's built-in test runner and `supertest` to exercise the Express app end-to-end against an in-memory SQLite database. It covers:

- Health check
- Full create / read / update / delete lifecycle
- Input validation (missing/empty title and author, invalid year)
- `?author=` query filter
- 404 and 400 error handling for unknown / invalid ids

## Design notes

- The Express app is produced by a `createApp()` factory that accepts a DB path or an injected `BookDb`, which makes it easy to test with an in-memory database.
- `better-sqlite3` is used synchronously for simple, predictable data access; prepared statements are reused for each query.
