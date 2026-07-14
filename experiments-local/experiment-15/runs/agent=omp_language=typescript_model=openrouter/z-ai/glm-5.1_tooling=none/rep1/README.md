# Book Collection API

A REST API for managing a book collection, built with Express and SQLite.

## Setup

```bash
npm install
```

## Run

```bash
npm start
```

The server starts on port 3000 (override with `PORT` env var). Data is stored in `books.db` (override with `DB_PATH` env var).

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| POST | /books | Create a book |
| GET | /books | List all books |
| GET | /books?author=X | Filter books by author |
| GET | /books/:id | Get a book by ID |
| PUT | /books/:id | Update a book |
| DELETE | /books/:id | Delete a book |

## Request Bodies

**POST /books** and **PUT /books/:id** accept JSON:

```json
{
  "title": "The Hobbit",
  "author": "J.R.R. Tolkien",
  "year": 1937,
  "isbn": "978-0261102217"
}
```

`title` and `author` are required. `year` and `isbn` are optional.

## Status Codes

- `200` — Success (GET, PUT)
- `201` — Created (POST)
- `204` — Deleted (DELETE)
- `400` — Validation error (missing title or author)
- `404` — Book not found

## Test

```bash
npm test
```

## Build

```bash
npm run build
```
