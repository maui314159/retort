# Book Collection API

A small REST API for managing a book collection, written in TypeScript with
[Express](https://expressjs.com/). Data is persisted in SQLite via Node's
built-in `node:sqlite` module — no native build step or external database
required.

## Requirements

- Node.js **22.5+** (the API uses the built-in `node:sqlite` module)
- npm

## Setup

```bash
npm install
```

## Build

```bash
npm run build      # compiles src/ -> dist/
```

## Run

```bash
npm start          # builds output must exist; runs dist/server.js
# or, build + run in one step:
npm run dev
```

The server listens on port `3000` by default. Override with environment
variables:

- `PORT` — listen port (default `3000`)
- `DB_PATH` — SQLite file path (default `books.db`)

```bash
PORT=8080 DB_PATH=/tmp/books.db npm run dev
```

## Tests

```bash
npm test           # compiles, then runs the node:test suite against an in-memory DB
```

## API

All request and response bodies are JSON.

| Method | Path           | Description                          | Success |
|--------|----------------|--------------------------------------|---------|
| GET    | `/health`      | Health check                         | 200     |
| POST   | `/books`       | Create a book                        | 201     |
| GET    | `/books`       | List books (optional `?author=`)     | 200     |
| GET    | `/books/{id}`  | Get a book by id                     | 200     |
| PUT    | `/books/{id}`  | Replace/update a book                | 200     |
| DELETE | `/books/{id}`  | Delete a book                        | 204     |

### Book shape

```jsonc
{
  "id": 1,
  "title": "Dune",      // required, non-empty string
  "author": "Herbert",  // required, non-empty string
  "year": 1965,         // optional integer, may be null
  "isbn": "978-..."     // optional string, may be null
}
```

### Validation & status codes

- `title` and `author` are required, non-empty strings. Missing/invalid input
  returns `400` with `{ "errors": [...] }`.
- `year` must be an integer if provided; `isbn` must be a string if provided.
- A non-numeric `{id}` returns `400`; an unknown `{id}` returns `404`.
- Malformed JSON bodies return `400`.

### Examples

```bash
# Create
curl -X POST localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Herbert","year":1965,"isbn":"978-0441013593"}'

# List, filtered by author
curl 'localhost:3000/books?author=Herbert'

# Get one
curl localhost:3000/books/1

# Update
curl -X PUT localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Herbert","year":1969}'

# Delete
curl -X DELETE localhost:3000/books/1
```

## Project layout

```
src/
  types.ts      # Book / BookInput interfaces
  db.ts         # BookStore — SQLite-backed persistence
  app.ts        # Express app factory (createApp) + validation
  server.ts     # HTTP entrypoint
  app.test.ts   # integration tests (node:test + supertest)
```
