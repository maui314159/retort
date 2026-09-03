# Book Collection API

A small REST API service for managing a book collection, written in **TypeScript** with **Express 5** and **SQLite** (via Node's built-in [`node:sqlite`](https://nodejs.org/api/sqlite.html) module — no native compilation or external database required).

## Features

- `POST   /books` — create a new book (`title`, `author`, `year`, `isbn`)
- `GET    /books` — list all books (supports `?author=` filtering, case-insensitive substring match)
- `GET    /books/:id` — get a single book by ID
- `PUT    /books/:id` — update (full replacement of) a book
- `DELETE /books/:id` — delete a book
- `GET    /health` — health check

### Validation

- `title` and `author` are **required** and must be non-empty strings (whitespace is trimmed).
- `year` is optional; when provided it must be a non-negative integer (numeric strings are accepted).
- `isbn` is optional; when provided it must be a string.
- Invalid input returns `400 Bad Request` with an `error` and a `details` map describing every offending field.

### HTTP status codes

| Route              | Success          | Errors                                    |
| ------------------ | ---------------- | ----------------------------------------- |
| `POST /books`      | `201 Created`    | `400` validation / bad JSON               |
| `GET /books`       | `200 OK`         |                                           |
| `GET /books/:id`   | `200 OK`         | `400` bad id, `404` not found             |
| `PUT /books/:id`   | `200 OK`         | `400` validation, `404` not found         |
| `DELETE /books/:id`| `204 No Content` | `400` bad id, `404` not found             |
| `GET /health`      | `200 OK`         |                                           |
| any other path     |                  | `404 Not Found`                           |

## Prerequisites

- **Node.js >= 22.5** (uses the built-in `node:sqlite` module; tested on Node 22)
- **npm**

## Setup

```bash
npm install
```

No native compilation step is required — SQLite is provided by Node itself, so the install is fast and self-contained.

## Running

### Development (with live TypeScript via tsx)

```bash
npm run dev
# -> Book collection API listening on http://0.0.0.0:3000
```

### Production (compiled)

```bash
npm run build     # compile TypeScript -> dist/
npm start         # -> node dist/server.js
```

### Configuration via environment variables

| Variable        | Default       | Description                                  |
| --------------- | ------------- | -------------------------------------------- |
| `PORT`          | `3000`        | Port to listen on                            |
| `HOST`          | `0.0.0.0`     | Host/interface to bind                       |
| `BOOKS_DB_PATH` | `./books.db`  | SQLite database file path. Use `:memory:` for an ephemeral in-memory database. |

Example:

```bash
PORT=8080 BOOKS_DB_PATH=/var/data/books.db npm start
```

## Testing

The test suite uses [Vitest](https://vitest.dev) and [Supertest](https://github.com/ladjs/supertest) against an in-memory SQLite store, so no files are written to disk during tests.

```bash
npm test              # run the full suite once
npm run test:watch    # run in watch mode
```

There are **23 tests** covering:
- Health check
- Book creation (happy path, missing `title`, missing `author`, empty strings, invalid `year`, malformed JSON)
- Listing and `?author=` filtering
- Fetching by id (found, not found, non-numeric id)
- Updating (success, not found, invalid input)
- Deletion (success, not found, idempotent 404)
- Unknown routes (404)
- The `validateBookInput` validator unit tests (trimming, negative-year rejection)

## Example usage

```bash
# Create a book
curl -X POST http://localhost:3000/books   -H 'Content-Type: application/json'   -d '{"title":"The Pragmatic Programmer","author":"Andrew Hunt","year":1999,"isbn":"978-0201616224"}'
# -> 201 {"id":1,"title":"The Pragmatic Programmer","author":"Andrew Hunt",...}

# List all books
curl http://localhost:3000/books

# Filter by author
curl 'http://localhost:3000/books?author=Andrew'

# Get / update / delete by id
curl http://localhost:3000/books/1
curl -X PUT http://localhost:3000/books/1 -H 'Content-Type: application/json'   -d '{"title":"New Title","author":"New Author","year":2000}'
curl -X DELETE http://localhost:3000/books/1
```

## Project layout

```
.
├── package.json
├── tsconfig.json
├── vitest.config.mts
├── README.md
└── src/
    ├── types.ts              # shared domain types
    ├── validation.ts         # input validation
    ├── db.ts                 # SQLite data-access layer (BookStore, node:sqlite)
    ├── app.ts                # Express app factory + routes
    ├── server.ts             # HTTP server entry point
    └── __tests__/
        └── books.test.ts     # integration + unit tests
```

## License

MIT
