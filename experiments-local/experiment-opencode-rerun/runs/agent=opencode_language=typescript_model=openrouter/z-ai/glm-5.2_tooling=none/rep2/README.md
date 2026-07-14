# Book Collection API

A REST API for managing a book collection, built with TypeScript, Express, and SQLite (via `better-sqlite3`).

## Features

- `POST /books` — Create a new book (`title`, `author`, `year`, `isbn`)
- `GET /books` — List all books (supports `?author=` filter)
- `GET /books/{id}` — Get a single book by ID
- `PUT /books/{id}` — Update a book
- `DELETE /books/{id}` — Delete a book
- `GET /health` — Health check

`title` and `author` are required on create/update. `year` (integer) and `isbn` are optional.

## Prerequisites

- Node.js 18+ (tested on Node 22)
- npm

## Setup

```bash
npm install
```

## Build

```bash
npm run build
```

## Run

```bash
npm start
# or for development with ts-node:
npm run dev
```

By default the server listens on port `3000` and uses `./books.db`. Override with environment variables:

```bash
PORT=4000 DB_PATH=/tmp/books.db npm start
```

## Tests

```bash
npm test
```

Tests run in-memory SQLite databases via `vitest` and `supertest`.

## Example

```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"1984","author":"George Orwell","year":1949,"isbn":"9780451524935"}'

curl http://localhost:3000/books
curl "http://localhost:3000/books?author=George%20Orwell"
curl http://localhost:3000/books/1
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Nineteen Eighty-Four","author":"George Orwell","year":1949}'
curl -X DELETE http://localhost:3000/books/1
```

## HTTP Status Codes

| Code | Meaning                         |
|------|---------------------------------|
| 200  | OK (GET, PUT)                   |
| 201  | Created (POST)                  |
| 204  | No Content (DELETE)             |
| 400  | Bad Request (validation error)  |
| 404  | Not Found                       |
