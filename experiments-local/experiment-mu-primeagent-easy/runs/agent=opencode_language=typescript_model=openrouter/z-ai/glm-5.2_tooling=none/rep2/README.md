# Book Collection API

A REST API service for managing a book collection, written in TypeScript with
Express and backed by SQLite (`better-sqlite3`).

## Features

- `POST /books` — Create a new book
- `GET /books` — List all books (supports `?author=` filtering, case-insensitive partial match)
- `GET /books/{id}` — Get a single book by ID
- `PUT /books/{id}` — Update a book (full replacement)
- `DELETE /books/{id}` — Delete a book
- `GET /health` — Health check endpoint

### Book fields

| field   | type   | required | notes                                   |
|---------|--------|----------|-----------------------------------------|
| title   | string | yes      | non-empty                               |
| author  | string | yes      | non-empty                               |
| year    | number | no       | integer between 0 and (current year + 1) |
| isbn    | string | no       |                                         |

Responses are JSON. Appropriate HTTP status codes are used (`201` on create,
`204` on delete, `400` on validation error, `404` when not found).

## Prerequisites

- Node.js 18+ (developed on Node 22)
- npm

## Setup

```bash
npm install
```

## Build

```bash
npm run build        # outputs compiled JS to ./dist
```

## Run

Start the server (listens on port 3000 by default, uses `books.db` in the
working directory):

```bash
npm start            # runs compiled output from dist/
# or, for development with auto-reload:
npm run dev
```

Configuration via environment variables:

| Variable  | default    | description                          |
|-----------|------------|--------------------------------------|
| `PORT`    | `3000`     | port the HTTP server listens on       |
| `DB_PATH` | `books.db` | path to the SQLite database file      |

Use `DB_PATH=:memory:` to run against an in-memory database.

## Test

```bash
npm test             # runs the vitest suite once
npm run test:watch   # runs in watch mode
npm run typecheck     # type-checks source + tests without emitting
```

The suite includes unit tests for input validation and integration tests that
exercise the full Express app over HTTP via `supertest` using an in-memory
SQLite database.

## Example requests

Create a book:

```bash
curl -sS -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"1984","author":"George Orwell","year":1949,"isbn":"978-0451524935"}'
```

List books, optionally filtered by author:

```bash
curl -sS http://localhost:3000/books
curl -sS 'http://localhost:3000/books?author=orwell'
```

## Project layout

```
src/
  db.ts          # SQLite data layer (BookStore)
  validation.ts # input validation for book payloads
  app.ts         # Express application (route definitions)
  index.ts       # server entry point
tests/
  health.test.ts     # health endpoint test
  books.test.ts      # API integration tests
  validation.test.ts # validation unit tests
```
