# Books API

A REST API for managing a book collection, built with **TypeScript**, **Express**, and **SQLite** (via `better-sqlite3`).

## Endpoints

| Method | Path            | Description                          |
|--------|-----------------|--------------------------------------|
| GET    | `/health`       | Health check                         |
| POST   | `/books`        | Create a book                        |
| GET    | `/books`        | List all books (supports `?author=`) |
| GET    | `/books/{id}`   | Get a single book                    |
| PUT    | `/books/{id}`   | Replace/update a book                |
| DELETE | `/books/{id}`   | Delete a book                        |

### Book shape

```json
{
  "id": 1,
  "title": "The Hobbit",
  "author": "J.R.R. Tolkien",
  "year": 1937,
  "isbn": "978-0261102217"
}
```

`title` and `author` are required. `year` (non-negative integer) and `isbn` (string) are optional.

## Prerequisites

- Node.js 18+ (developed on Node 22)

## Setup

```bash
npm install
npm run build
```

## Run

```bash
npm start
# or for development with auto-reload:
npm run dev
```

By default the server listens on `http://localhost:3000` and stores data in `./data/books.sqlite`.

### Configuration (env vars)

- `PORT` — HTTP port (default `3000`)
- `DB_PATH` — SQLite file path (default `./data/books.sqlite`)

## Test

```bash
npm test
```

Tests are integration tests using `supertest` against an in-memory SQLite database; no external services required.

## Example

```bash
curl -s localhost:3000/health
curl -s -X POST localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Hobbit","author":"Tolkien","year":1937,"isbn":"978-0261102217"}'
curl -s 'localhost:3000/books?author=Tolkien'
```
