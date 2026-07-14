# Book Collection API

A REST API for managing a book collection, built with **TypeScript** on **Bun** and backed by **SQLite** (`bun:sqlite`).

## Requirements

- [Bun](https://bun.sh) ≥ 1.3 (ships its own TypeScript, SQLite, and test runner — no other dependencies required)

Install runtime deps (dev types only):

```bash
bun install
```

## Running

```bash
bun run start          # production-style run
bun run dev            # auto-reloading on file changes
```

By default the server listens on `http://localhost:3000` and persists data to `./books.db`. Override with env vars:

```bash
PORT=4000 DB_PATH=/var/lib/books.db bun run start
```

## Endpoints

| Method   | Path          | Description                          |
|----------|---------------|--------------------------------------|
| `GET`    | `/health`     | Health check → `{"status":"ok"}`     |
| `GET`    | `/books`      | List all books; supports `?author=`  |
| `GET`    | `/books/{id}` | Get a single book                    |
| `POST`   | `/books`      | Create a book (returns `201`)        |
| `PUT`    | `/books/{id}` | Update a book (partial fields OK)    |
| `DELETE` | `/books/{id}` | Delete a book                        |

### Book shape

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "978-0441172719"
}
```

- `title` and `author` are **required** (non-empty strings) on create.
- `year` is an integer 0–9999 (or `null`).
- `isbn` is a string (or `null`).
- `PUT` accepts a partial body; omitted fields keep their existing values.

### Status codes

| Code | Meaning                          |
|------|----------------------------------|
| 200  | OK                               |
| 201  | Created                          |
| 400  | Malformed JSON body              |
| 404  | Book or route not found          |
| 405  | Method not allowed (`Allow` set) |
| 422  | Validation failed (`errors[]`)   |

### Examples

```bash
# Create
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'

# List, filtered by author
curl "http://localhost:3000/books?author=Frank%20Herbert"

# Update year only
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"year":2020}'

# Delete
curl -X DELETE http://localhost:3000/books/1
```

## Project layout

```
src/
  main.ts         # entrypoint: wires store + server, handles signals
  server.ts       # HTTP routing & request/response helpers
  db.ts           # SQLite-backed BookStore (prepared statements)
  validation.ts   # input validation for create / partial update
  types.ts        # shared types
test/
  validation.test.ts  # validation unit tests
  store.test.ts       # SQLite store unit tests
  api.test.ts         # HTTP integration tests (real server, in-memory DB)
```

## Testing

```bash
bun test              # run all tests
bun run typecheck     # tsc --noEmit
```

The HTTP integration tests boot a real `Bun.serve` instance on an ephemeral port backed by an in-memory SQLite database, so they exercise the full request→routing→store→response path.
