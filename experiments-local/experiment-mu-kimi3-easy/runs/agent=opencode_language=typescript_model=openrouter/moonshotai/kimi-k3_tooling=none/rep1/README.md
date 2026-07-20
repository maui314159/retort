# Book Collection API

A REST API service for managing a book collection, written in TypeScript and
backed by SQLite. It has **zero runtime dependencies** — it uses Node.js
built-ins only (`node:http` for the server, `node:sqlite` for storage).

## Requirements

- Node.js **>= 22.18** (runs TypeScript natively via type stripping; no
  transpile step needed to run from source)
- npm (only for installing the dev tooling used by `build` / `typecheck`)

## Setup

```sh
npm install
```

## Run

```sh
npm start
```

The server listens on `http://localhost:3000` and stores data in `books.db`
in the current directory. Both can be overridden with environment variables:

```sh
PORT=8080 DB_PATH=/tmp/mybooks.db npm start
```

## Build and typecheck

```sh
npm run typecheck   # strict type check of src + tests (no emit)
npm run build       # compile src to plain JS in dist/
node dist/index.js  # run the compiled output
```

## Test

```sh
npm test
```

Runs the integration test suite in `tests/` against a live server instance
backed by an in-memory SQLite database, using Node's built-in test runner.

## API

All responses are JSON. Errors are returned as `{ "error": "<message>" }`
with an appropriate 4xx/5xx status code.

| Method | Path           | Description                              | Success status |
| ------ | -------------- | ---------------------------------------- | -------------- |
| GET    | `/health`      | Health check                             | 200            |
| POST   | `/books`       | Create a book                            | 201            |
| GET    | `/books`       | List all books; `?author=` filters       | 200            |
| GET    | `/books/:id`   | Get a single book by ID                  | 200            |
| PUT    | `/books/:id`   | Replace a book                           | 200            |
| DELETE | `/books/:id`   | Delete a book                            | 204            |

### Book fields

- `title` (string, **required**, non-empty)
- `author` (string, **required**, non-empty)
- `year` (integer, optional)
- `isbn` (string, optional)

Books are returned with an integer `id` plus the fields above
(`year`/`isbn` are `null` when not set).

### Examples

```sh
# Create
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937, "isbn": "978-0-261-10221-7"}'

# List (optionally filtered)
curl http://localhost:3000/books
curl 'http://localhost:3000/books?author=J.R.R.%20Tolkien'

# Get one
curl http://localhost:3000/books/1

# Update (full replace)
curl -X PUT http://localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "The Hobbit (Revised)", "author": "J.R.R. Tolkien", "year": 1951}'

# Delete
curl -X DELETE http://localhost:3000/books/1

# Health
curl http://localhost:3000/health
```

## Project layout

```
src/
  index.ts       entry point — opens the DB and starts the server
  server.ts      HTTP routing and request/response handling
  db.ts          SQLite schema and CRUD helpers (node:sqlite)
  validation.ts  request payload validation (title/author required)
  types.ts       Book / BookInput types
tests/
  books.test.ts  integration tests (node:test)
```
