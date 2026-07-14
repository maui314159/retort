# Book Collection API

A REST API service for managing a book collection, built with **TypeScript**, **Express**, and **SQLite** (`better-sqlite3`).

## Requirements

- Node.js 18+
- npm

## Setup

```bash
npm install
npm run build
```

## Run

```bash
npm start
```

The server starts on `http://localhost:3000` (override with `PORT` env var).

By default the SQLite database file is `./books.db`. Override with the
`BOOK_DB_PATH` env var.

## Development

```bash
npm run dev    # run with ts-node (no build step)
npm test       # run Jest test suite
npm run typecheck
```

## Endpoints

| Method | Path            | Description                          |
|--------|-----------------|--------------------------------------|
| GET    | `/health`       | Health check → `200 { "status": "ok" }` |
| POST   | `/books`        | Create a book                        |
| GET    | `/books`        | List all books (supports `?author=`) |
| GET    | `/books/{id}`   | Get a single book by ID              |
| PUT    | `/books/{id}`   | Update a book                        |
| DELETE | `/books/{id}`   | Delete a book                        |

### Book schema

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441172719"
}
```

`title` and `author` are **required** and must be non-empty strings.
`year` (integer) and `isbn` (string) are optional and may be `null`.

### Status codes

- `200` — successful GET / PUT
- `201` — successful POST
- `204` — successful DELETE
- `400` — validation error (JSON `{ "errors": [...] }`)
- `404` — book not found

## Example

```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

curl http://localhost:3000/books?author=Frank%20Herbert
```

## Tests

The Jest suite covers the health check, the full CRUD lifecycle, author
filtering, and input validation (4 tests across 3 describe blocks).

```bash
npm test
```
