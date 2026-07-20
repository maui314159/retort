# Book Collection API

A REST API service for managing a book collection, built with TypeScript, Express, and SQLite (via `better-sqlite3`).

## Endpoints

| Method | Path          | Description                                      |
| ------ | ------------- | ------------------------------------------------ |
| GET    | `/health`     | Health check — returns `{"status":"ok"}`         |
| POST   | `/books`      | Create a book (`title`, `author` required; `year`, `isbn` optional) |
| GET    | `/books`      | List all books; supports `?author=` exact-match filter |
| GET    | `/books/:id`  | Get a single book by ID                          |
| PUT    | `/books/:id`  | Update a book (partial updates supported)        |
| DELETE | `/books/:id`  | Delete a book                                    |

All responses are JSON with appropriate HTTP status codes (`201` on create, `204` on delete, `400` on validation errors, `404` when a book is not found).

## Setup

Requires Node.js 18+ (developed on Node 22).

```sh
npm install
```

## Run

```sh
npm start          # starts on http://localhost:3000, stores data in ./books.db
```

Configuration via environment variables:

- `PORT` — listen port (default `3000`)
- `DB_FILE` — SQLite database file (default `books.db`); use `:memory:` for an ephemeral store

Other scripts:

```sh
npm run dev        # watch mode
npm run build      # compile TypeScript to dist/
npm run typecheck  # type-check without emitting
```

## Test

```sh
npm test
```

Runs 7 integration tests (vitest + supertest) against an in-memory SQLite database, covering the health check, creation, validation errors, listing with the author filter, single-fetch, update, and deletion.

## Example

```sh
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

curl "http://localhost:3000/books?author=Frank%20Herbert"
```

## Project layout

```
src/db.ts       SQLite setup and Book type
src/app.ts      Express app factory (routes + validation)
src/server.ts   Entrypoint — wires the DB to the app and listens
tests/          vitest + supertest integration tests
```
