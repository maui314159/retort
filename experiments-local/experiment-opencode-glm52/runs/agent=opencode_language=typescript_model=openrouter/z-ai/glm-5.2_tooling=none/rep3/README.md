# Books API

A REST API for managing a book collection, written in TypeScript with Express and SQLite (via `better-sqlite3`).

## Features

- `POST /books` — Create a new book (`title`, `author`, `year`, `isbn`)
- `GET /books` — List all books (supports `?author=` filter)
- `GET /books/{id}` — Get a single book by ID
- `PUT /books/{id}` — Update a book
- `DELETE /books/{id}` — Delete a book
- `GET /health` — Health check endpoint
- Input validation: `title` and `author` are required
- JSON responses with appropriate HTTP status codes
- Data persisted in an embedded SQLite database

## Prerequisites

- Node.js 18+ (developed on Node 22)
- npm

## Setup

```bash
npm install
```

## Build

```bash
npm run build
```

This compiles the TypeScript in `src/` into `dist/`.

## Run

Start the server (default port `3000`):

```bash
npm start
```

Or run directly from TypeScript source during development:

```bash
npm run dev
```

### Configuration

| Variable   | Default              | Description                       |
| ---------- | -------------------- | --------------------------------- |
| `PORT`     | `3000`               | Port the HTTP server listens on  |
| `DB_PATH`  | `./books.db`         | Path to the SQLite database file |

Example:

```bash
PORT=8080 DB_PATH=/tmp/books.db npm start
```

## Usage examples

Create a book:

```bash
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937,"isbn":"9780261102217"}'
```

List books (optionally filter by author):

```bash
curl http://localhost:3000/books
curl 'http://localhost:3000/books?author=J.R.R.%20Tolkien'
```

Get a book by ID:

```bash
curl http://localhost:3000/books/1
```

Update a book:

```bash
curl -X PUT http://localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year":1938}'
```

Delete a book:

```bash
curl -X DELETE http://localhost:3000/books/1
```

Health check:

```bash
curl http://localhost:3000/health
```

## Tests

Tests use [Vitest](https://vitest.dev) and [supertest](https://github.com/ladjs/supertest). Each test uses an in-memory SQLite database so no cleanup is required.

```bash
npm test
```

Run in watch mode:

```bash
npm run test:watch
```

## Project structure

```
src/
  app.ts        # Express app factory
  routes.ts     # Route handlers + validation
  db.ts         # SQLite connection and book repository
  server.ts     # HTTP server entrypoint
tests/
  books.test.ts # Integration tests
```
