# Book Collection API

A REST API service for managing a book collection, built with **TypeScript**, **Express**, and **SQLite** (via `better-sqlite3`).

## Endpoints

| Method | Path             | Description                          |
|--------|------------------|--------------------------------------|
| GET    | `/health`        | Health check                         |
| POST   | `/books`         | Create a book (title, author, year, isbn) |
| GET    | `/books`         | List all books (supports `?author=` filter) |
| GET    | `/books/{id}`    | Get a single book by ID              |
| PUT    | `/books/{id}`    | Update a book                        |
| DELETE | `/books/{id}`    | Delete a book                        |

`title` and `author` are required. `year` must be a non-negative integer; `isbn` is an optional string.

## Setup

```bash
npm install
```

## Run

In-memory database (default):

```bash
npm run build
npm start
```

Persistent SQLite file:

```bash
DB_PATH=./books.db PORT=3000 npm start
```

Development with live reload:

```bash
npm run dev
```

The server listens on `http://localhost:3000` (override with `PORT`).

## Tests

```bash
npm test
```

Tests use `vitest` + `supertest` and cover the full CRUD flow, input validation, the author filter, and 404 handling.

## Example

```bash
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"1984","author":"George Orwell","year":1949,"isbn":"978-0451524935"}'

curl http://localhost:3000/books?author=George%20Orwell
```
