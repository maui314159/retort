# Book Collection API

A small REST API for managing a book collection. Written in TypeScript on
Express, persisted to SQLite via `better-sqlite3`, validated with `zod`,
and tested with `vitest` + `supertest`.

## Endpoints

| Method | Path           | Description                              | Success |
| ------ | -------------- | ---------------------------------------- | ------- |
| GET    | `/health`      | Liveness probe; reports DB reachability. | 200     |
| POST   | `/books`       | Create a book.                           | 201     |
| GET    | `/books`       | List books (optional `?author=` filter). | 200     |
| GET    | `/books/{id}`  | Get a single book.                       | 200     |
| PUT    | `/books/{id}`  | Update a book.                           | 200     |
| DELETE | `/books/{id}`  | Delete a book.                           | 204     |

### Book payload

```json
{
  "title":  "Dune",
  "author": "Frank Herbert",
  "year":   1965,
  "isbn":   "978-0441172719"
}
```

- `title` and `author` are required (non-empty after trimming).
- `year` must be an integer in the range `-3000..9999`. Nullable.
- `isbn` is optional, up to 32 characters; empty strings are normalised to
  `null`. Nullable.

Error responses look like:

```json
{ "error": "ValidationError", "details": { "fieldErrors": {}, "formErrors": [] } }
```

## Requirements

- Node.js 20+ (developed and tested on 22).
- A C toolchain capable of building `better-sqlite3`'s native module
  (Xcode CLT on macOS, `build-essential` on Debian/Ubuntu, or MSVC Build
  Tools on Windows).

## Setup

```bash
npm install
```

This downloads the runtime + dev dependencies and compiles
`better-sqlite3`'s native module.

## Run

### Production

```bash
npm run build       # compile TypeScript -> dist/
npm start           # node dist/index.js
```

The server listens on `http://localhost:3000` by default. Override with
the `PORT` environment variable. SQLite data is written to
`./data/books.sqlite` by default; override with `BOOKS_DB_PATH`.

### Development (auto-reload)

```bash
npm run dev
```

`tsx watch` recompiles and restarts on every save.

## Test

```bash
npm test
```

`vitest` runs the integration suite against an in-memory database. The
suite covers happy paths, validation, 404s, and 400s for every endpoint.

## Example session

```bash
# health
curl -s http://localhost:3000/health

# create
curl -s -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'

# list filtered by author
curl -s 'http://localhost:3000/books?author=Frank%20Herbert'

# fetch one
curl -s http://localhost:3000/books/1

# update
curl -s -X PUT http://localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year":1966}'

# delete
curl -s -X DELETE http://localhost:3000/books/1 -i
```

## Layout

```
src/
  app.ts            # Express factory, middleware, error handler
  books.ts          # BookRepository over better-sqlite3
  db.ts             # Connection + schema bootstrap
  routes/books.ts   # /books router
  validation.ts     # zod schemas for create + update
  index.ts          # Server entry point
tests/
  books.test.ts     # Integration suite
```

## Environment variables

| Variable          | Default              | Notes                              |
| ----------------- | -------------------- | ---------------------------------- |
| `PORT`            | `3000`               | HTTP listen port.                  |
| `BOOKS_DB_PATH`   | `./data/books.sqlite`| SQLite file. `:memory:` is valid.  |
| `NODE_ENV`        | _(unset)_            | When `test`, the in-memory DB is used by default. |
