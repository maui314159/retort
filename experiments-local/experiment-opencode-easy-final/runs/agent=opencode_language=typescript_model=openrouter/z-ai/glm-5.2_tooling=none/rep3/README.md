# Book Collection REST API

A small REST API for managing a book collection, written in TypeScript with
Express, SQLite (`better-sqlite3`) for storage, and `zod` for input
validation.

## Requirements

- Node.js 18+ (tested on Node 20)
- npm

## Setup

```bash
npm install
npm run build
```

## Running

Start the server (default port 3000):

```bash
npm start
```

Override the port or database location via env vars:

```bash
PORT=4000 DB_PATH=/tmp/books.db npm start
```

A `books.db` file is created in the working directory on first run.

## Endpoints

| Method   | Path           | Description                          |
| -------- | -------------- | ------------------------------------ |
| `GET`    | `/health`      | Health check (verifies DB connection)|
| `POST`   | `/books`       | Create a book                        |
| `GET`    | `/books`       | List books (supports `?author=`)     |
| `GET`    | `/books/:id`   | Get a single book by ID              |
| `PUT`    | `/books/:id`   | Update a book                        |
| `DELETE` | `/books/:id`   | Delete a book                        |

### Book shape

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441172719",
  "created_at": "2026-01-01T00:00:00.000Z",
  "updated_at": "2026-01-01T00:00:00.000Z"
}
```

### Validation rules

- `title` and `author` are required (non-empty strings, max 500 chars).
- `year` is an optional integer between 0 and 9999.
- `isbn` is an optional string up to 100 chars.
- On validation failure the API responds with `400` and a body like:

```json
{
  "message": "Validation failed",
  "details": [{ "path": "title", "message": "title is required", "code": "too_small" }]
}
```

### Status codes

| Code | Meaning                          |
| ---- | -------------------------------- |
| 200  | Success (GET, PUT)               |
| 201  | Created (POST)                   |
| 204  | No content (DELETE)              |
| 400  | Validation / malformed request   |
| 404  | Book or route not found          |
| 500  | Internal server error            |
| 503  | Health check DB unreachable      |

## Examples

```bash
# Create
curl -sX POST localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

# List all
curl -s localhost:3000/books

# Filter by author
curl -s 'localhost:3000/books?author=Frank%20Herbert'

# Get one
curl -s localhost:3000/books/1

# Update
curl -sX PUT localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year":1966}'

# Delete
curl -sX DELETE localhost:3000/books/1
```

## Tests

Unit + integration tests use `vitest` and `supertest`. Each test gets an
isolated SQLite file in a temp directory.

```bash
npm test            # run once
npm run test:watch  # watch mode
npm run typecheck   # tsc --noEmit
```

## Project layout

```
src/
  server.ts     # Express app + process lifecycle
  books.ts      # /books routes
  health.ts     # /health route
  db.ts         # SQLite connection + migrations
  validation.ts # zod schemas
tests/
  books.test.ts # integration tests
```
