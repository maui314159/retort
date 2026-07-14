# Book Collection API

A REST API service for managing a book collection, built with TypeScript, Express, and SQLite (via `better-sqlite3`).

## Features

- `POST /books` — Create a new book (`title`, `author`, `year`, `isbn`)
- `GET /books` — List all books (supports `?author=` filter)
- `GET /books/{id}` — Get a single book by ID
- `PUT /books/{id}` — Update a book
- `DELETE /books/{id}` — Delete a book
- `GET /health` — Health check endpoint

`title` and `author` are required. `year` (integer) and `isbn` (string) are optional.

## Prerequisites

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

This compiles the TypeScript source in `src/` to `dist/`.

## Run

Start the server (uses `./books.db` by default):

```bash
npm start
```

For development with `ts-node`:

```bash
npm run dev
```

### Configuration

| Env var    | Default        | Description                            |
|------------|----------------|----------------------------------------|
| `PORT`     | `3000`         | Port the HTTP server listens on        |
| `DB_PATH`  | `./books.db`   | SQLite database file path              |

Use `DB_PATH=:memory:` for an ephemeral in-memory database.

## Usage examples

Create a book:

```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
```

List all books:

```bash
curl http://localhost:3000/books
```

Filter by author:

```bash
curl "http://localhost:3000/books?author=Frank%20Herbert"
```

Get, update, and delete by ID:

```bash
curl http://localhost:3000/books/1
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"year":1966}'
curl -X DELETE http://localhost:3000/books/1
```

Health check:

```bash
curl http://localhost:3000/health
```

## Tests

```bash
npm test
```

Tests use `jest`, `ts-jest`, and `supertest` and run against an in-memory SQLite database so they are isolated and repeatable. They cover the health check, CRUD operations, input validation, the `?author=` filter, and error cases (404s, invalid input).

## Project structure

```
src/
  app.ts          # Express app factory and routes
  bookStore.ts    # SQLite-backed data access layer
  server.ts       # HTTP server entry point
  types.ts        # Shared TypeScript types
  validation.ts   # Input validation helpers
tests/
  books.test.ts   # Integration tests
```
