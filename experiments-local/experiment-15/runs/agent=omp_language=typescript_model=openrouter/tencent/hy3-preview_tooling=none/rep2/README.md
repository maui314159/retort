# Book Collection API

REST API service for managing a book collection, built with TypeScript, Express, and SQLite.

## Prerequisites

- Node.js 18+
- npm

## Setup

```bash
npm install
```

## Build

```bash
npm run build
```

Compiles TypeScript to `dist/`.

## Run

```bash
npm start
```

API listens on `http://localhost:3000` (set `PORT` env var to override).

## Development

```bash
# Build and run tests
npm test
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/books` | Create a book |
| GET | `/books` | List all books (query param `?author=` filters by author) |
| GET | `/books/:id` | Get a single book by ID |
| PUT | `/books/:id` | Update a book |
| DELETE | `/books/:id` | Delete a book |
| GET | `/health` | Health check |

## Request / Response Examples

**Create a book** — `POST /books`

```json
{ "title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935" }
```

Returns `201` with the created book including its assigned `id`. `title` and `author` are required; `year` and `isbn` are optional.

**List books** — `GET /books`

Returns `200` with a JSON array of all books.

Filter by author: `GET /books?author=Orwell`

**Get a book** — `GET /books/1`

Returns `200` with the book, or `404` if not found.

**Update a book** — `PUT /books/1`

Send any subset of `{ "title", "author", "year", "isbn" }`. Returns `200` with the updated book, or `404` if not found.

**Delete a book** — `DELETE /books/1`

Returns `204` on success, `404` if not found.

**Health check** — `GET /health`

Returns `200` with `{ "status": "ok" }`.

## Data Storage

Uses SQLite via `better-sqlite3`. Defaults to an in-memory database.
To use a file-based database, set the `DB_PATH` environment variable:

```bash
DB_PATH=./books.db npm start
```

## Run Tests

```bash
npm test
```

Runs 14 integration tests covering all endpoints and validation.
