# Books API

A REST API service for managing a book collection, built with **TypeScript**, **Express**, and **SQLite** (`better-sqlite3`).

## Features

- `POST /books` — create a new book (`title`, `author`, `year`, `isbn`)
- `GET /books` — list all books (supports `?author=` filter)
- `GET /books/{id}` — get a single book by ID
- `PUT /books/{id}` — update a book (any subset of fields)
- `DELETE /books/{id}` — delete a book
- `GET /health` — health check

## Requirements

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

Compiles TypeScript in `src/` to `dist/`.

## Run

```bash
npm start
```

Starts the server from `dist/server.js`. By default it listens on port `3000` and persists data to `books.db` (SQLite) in the working directory.

### Configuration (environment variables)

| Variable   | Default       | Description                              |
|------------|---------------|------------------------------------------|
| `PORT`     | `3000`        | Port the HTTP server listens on          |
| `DB_PATH`  | `books.db`    | SQLite database file path                |

Example:

```bash
PORT=4000 DB_PATH=/tmp/books.db npm start
```

### Development mode (no build step)

```bash
npm run dev
```

Runs the server directly from TypeScript via `ts-node`, using an in-memory database by default — override with `DB_PATH`.

## API examples

Create a book:

```bash
curl -s -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Pragmatic Programmer","author":"Andy Hunt","year":1999,"isbn":"978-0201616224"}'
```

List books:

```bash
curl -s http://localhost:3000/books
curl -s 'http://localhost:3000/books?author=Andy%20Hunt'
```

Get / update / delete:

```bash
curl -s http://localhost:3000/books/1
curl -s -X PUT http://localhost:3000/books/1 -H 'Content-Type: application/json' -d '{"year":2019}'
curl -s -o /dev/null -w '%{http_code}\n' -X DELETE http://localhost:3000/books/1
```

Health check:

```bash
curl -s http://localhost:3000/health
# {"status":"ok"}
```

### Validation rules

- `title` and `author` are required and must be non-empty strings (on create).
- On update, any provided `title`/`author` must also be non-empty if present.
- `year` must be an integer (or `null`) in a sane range.
- `isbn` must be a string (or `null`).
- Invalid input returns `400` with `{ "error": "<message>" }`.
- Unknown book IDs return `404`.

### HTTP status codes

| Code | Meaning                              |
|------|--------------------------------------|
| 200  | Success (GET, PUT)                   |
| 201  | Created (POST)                       |
| 204  | No content (DELETE)                  |
| 400  | Bad request / validation error       |
| 404  | Book not found                       |

## Tests

The project uses [Vitest](https://vitest.dev) and [supertest](https://github.com/ladjs/supertest). Tests run against an in-memory SQLite database, so no cleanup is needed.

```bash
npm test
```

Run in watch mode during development:

```bash
npm run test:watch
```

### Test coverage

- `tests/books.test.ts` — integration tests covering health check, full CRUD flow, validation errors, 404 handling, and the `?author=` filter.
- `tests/store.test.ts` — unit tests for the `BookStore` SQLite persistence layer (create, list, filter, update, delete).

## Project structure

```
.
├── src/
│   ├── app.ts      # Express app factory + routes + validation
│   ├── db.ts       # SQLite-backed BookStore
│   └── server.ts   # HTTP server entrypoint
├── tests/
│   ├── books.test.ts
│   └── store.test.ts
├── package.json
├── tsconfig.json
└── README.md
```
