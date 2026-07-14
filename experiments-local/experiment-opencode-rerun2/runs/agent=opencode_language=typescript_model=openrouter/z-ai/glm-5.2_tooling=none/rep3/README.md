# Books API

A small REST API for managing a book collection, written in **TypeScript** with **Express**, **better-sqlite3** (embedded SQLite), and **Zod** for input validation. Tests run on **Vitest** + **Supertest**.

## Endpoints

| Method     | Path           | Description                                |
|------------|----------------|--------------------------------------------|
| `GET`      | `/health`       | Liveness/health check → `{"status":"ok"}` |
| `POST`     | `/books`         | Create a book (`title`, `author` required; `year`, `isbn` optional) |
| `GET`      | `/books`         | List books; supports `?author=` filter       |
| `GET`      | `/books/{id}`     | Fetch a single book by id                   |
| `PUT`      | `/books/{id}`      | Partial or full update of a book            |
| `DELETE`   | `/books/{id}`      | Delete a book                                |

### Status codes

- `200 OK` — successful read/update, health
- `201 Created` — book created
- `204 No Content` — book deleted
- `400 Bad Request` — malformed id or JSON body
- `404 Not Found` — book or route does not exist
- `422 Unprocessable Entity` — Zod validation failure (e.g. missing `title`/`author`)
- `500 Internal Server Error` — unexpected error

## Setup

Requirements: Node.js 18+ (uses native ESM).

```bash
npm install
```

### Build

```bash
npm run build         # tsc -> dist/
```

### Run

```bash
npm start             # runs dist/server.js
# or, in development with hot reload:
npm run dev
```

By default the server listens on `http://localhost:3000` and writes a SQLite
file `books.db` in the working directory. Override via environment variables:

```bash
PORT=4000 DB_PATH=/tmp/books.db npm start
```

### Example

```bash
curl -s -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Pragmatic Programmer","author":"Andy Hunt","year":1999,"isbn":"978-0201616224"}'

curl -s 'http://localhost:3000/books?author=Andy%20Hunt'
```

## Tests

```bash
npm test              # vitest run, one shot
npm run test:watch    # vitest watch mode
```

The suite (`tests/books.test.ts`) spins up a fresh temporary SQLite database
for each test using `supertest` against the real Express app. It covers:

- `GET /health`
- `POST /books` create + validation (missing `title`/`author`, optional fields)
- `GET /books` list and `?author=` filtering
- `GET /books/:id` happy path + 404 + malformed id
- `PUT /books/:id` full + partial update + validation + 404
- `DELETE /books/:id` happy path + 404
- unknown route 404

## Project layout

```
package.json
tsconfig.json
src/
  db.ts           SQLite open + Book type
  validation.ts   Zod schemas + normalizers
  books.ts        BooksService + Express router
  server.ts       App factory + main entrypoint
tests/
  books.test.ts   Integration tests
```
