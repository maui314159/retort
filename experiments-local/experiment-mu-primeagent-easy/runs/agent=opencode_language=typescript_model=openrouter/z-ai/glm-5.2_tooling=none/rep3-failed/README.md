# Book Collection REST API

A small REST API for managing a book collection, built with TypeScript, Express, and SQLite (via `better-sqlite3`).

## Endpoints

| Method | Path             | Description                          |
|--------|------------------|--------------------------------------|
| GET    | `/health`        | Health check                         |
| POST   | `/books`         | Create a new book                    |
| GET    | `/books`         | List all books (supports `?author=`) |
| GET    | `/books/{id}`    | Get a single book                    |
| PUT    | `/books/{id}`    | Update a book                        |
| DELETE | `/books/{id}`    | Delete a book                        |

### Book fields
- `title` (string, **required**)
- `author` (string, **required**)
- `year` (integer, optional)
- `isbn` (string, optional)

### Status codes
- `200` – successful read / update
- `201` – created
- `204` – deleted
- `400` – validation error
- `404` – book not found

## Setup

```bash
npm install
npm run build
```

## Run

```bash
npm start
# or run directly from source:
npm run dev
```

By default the server listens on `http://localhost:3000` and persists data to `books.db`. Override via environment variables:

```bash
PORT=4000 DB_PATH=/tmp/books.db npm start
```

For an in-memory database (e.g. for quick experiments):

```bash
DB_PATH=:memory: npm start
```

## Tests

```bash
npm test
```

Tests use Mocha + Chai + Supertest. They run against an in-memory SQLite database and cover both the HTTP API and the data store directly.

## Example

```bash
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

curl http://localhost:3000/books?author=Frank%20Herbert
```
