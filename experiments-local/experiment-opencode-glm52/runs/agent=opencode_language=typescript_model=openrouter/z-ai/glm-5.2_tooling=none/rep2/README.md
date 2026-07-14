# Books API

A REST API service for managing a book collection, written in TypeScript with Express and SQLite.

## Requirements

- Node.js 18+ (tested on Node 22)
- npm

## Setup

```bash
npm install
npm run build
```

## Running

```bash
npm start
# or
npm run dev
```

The server listens on `http://localhost:3000` by default. Override with the `PORT` environment variable:

```bash
PORT=4000 npm start
```

On first run against a file-backed database, the `books` table is created automatically if it does not exist. An in-memory database is used by the test suite.

## Endpoints

| Method   | Path          | Description                                  |
| -------- | ------------- | -------------------------------------------- |
| `GET`    | `/health`     | Health check (`{"status":"ok"}`)           |
| `POST`   | `/books`      | Create a book (title, author, year, isbn)  |
| `GET`    | `/books`      | List all books; supports `?author=` filter |
| `GET`    | `/books/:id`  | Get a single book by ID                 |
| `PUT`    | `/books/:id`  | Update a book                              |
| `DELETE` | `/books/:id`  | Delete a book                                |

### Book shape

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-..." }
```

`title` and `author` are required. `year` (integer) and `isbn` (string) are optional and may be `null`.

### Status codes

- `200` — successful GET / PUT
- `201` — successful POST
- `204` — successful DELETE
- `400` — validation error (returns `{ "errors": [...] }`)
- `404` — book not found
- `500` — internal server error

## Example

```bash
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

curl 'http://localhost:3000/books?author=Frank%20Herbert'
```

## Tests

```bash
npm test
```

Tests use `vitest` + `supertest` against an in-memory SQLite database. The suite covers:

- `GET /health` returns the expected payload
- `POST /books` validates required `title`/`author` and accepts optional fields
- `GET /books` lists all and filters by `?author=`
- `GET/PUT/DELETE /books/:id` cover success and 404 paths
- Invalid update bodies are rejected with 400

## Project layout

```
src/
  db.ts             SQLite setup + Book types
  validation.ts     zod-based input validation
  routes/books.ts   /books router
  routes/health.ts  /health router
  server.ts         Express app factory + entrypoint
tests/
  books.test.ts     integration tests
```
