# Book API

A REST API service for managing a book collection, built with **TypeScript**, **Express**, and **SQLite** (`better-sqlite3`).

## Features

- `POST /books` — Create a new book (`title`, `author`, `year`, `isbn`)
- `GET /books` — List all books (supports `?author=` filter)
- `GET /books/{id}` — Get a single book by ID
- `PUT /books/{id}` — Update a book
- `DELETE /books/{id}` — Delete a book
- `GET /health` — Health check endpoint
- Input validation (`title` and `author` are required and must be non-empty strings)
- SQLite-backed persistence (in-memory by default, or a file via `DB_PATH`)
- JSON responses with appropriate HTTP status codes

## Prerequisites

- Node.js 20+ (tested on Node 22)

## Setup

```bash
npm install
```

## Build

```bash
npm run build
```

Outputs compiled JavaScript to `dist/`.

## Run

Start the server (defaults to port 3000, in-memory SQLite):

```bash
npm start
```

Run from source without compiling:

```bash
npm run dev
```

### Configuration (environment variables)

| Variable  | Default     | Description                                     |
| --------- | ----------- | ----------------------------------------------- |
| `PORT`    | `3000`      | Port the HTTP server listens on                 |
| `DB_PATH` | `:memory:`  | SQLite database path. Use a file path to persist |

Persist to a file:

```bash
DB_PATH=./books.db npm start
```

## Example usage

```bash
# Create
curl -s -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Clean Code","author":"Robert C. Martin","year":2008,"isbn":"978-0132350884"}'

# List
curl -s http://localhost:3000/books

# List filtered by author
curl -s 'http://localhost:3000/books?author=Robert%20C.%20Martin'

# Get one (replace <id>)
curl -s http://localhost:3000/books/<id>

# Update
curl -s -X PUT http://localhost:3000/books/<id> \
  -H 'Content-Type: application/json' \
  -d '{"title":"Clean Code 2nd","author":"Robert C. Martin","year":2020,"isbn":null}'

# Delete
curl -s -X DELETE http://localhost:3000/books/<id> -i
```

## Tests

Unit + integration tests using `vitest` and `supertest`:

```bash
npm test
```

The test suite covers:
1. The `GET /health` health check.
2. Full CRUD flow (create → list → get → update → delete → 404).
3. Input validation (missing/empty `title` and `author`).
4. The `?author=` filter.
5. 404 handling for unknown IDs on GET/PUT/DELETE.

## Project structure

```
.
├── package.json
├── tsconfig.json
├── README.md
├── src
│   ├── db.ts        # SQLite setup, validation, and data access functions
│   ├── routes.ts    # Express router with all endpoints
│   └── server.ts    # App factory and server bootstrap
└── tests
    └── books.test.ts
```
