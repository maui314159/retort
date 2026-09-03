# Book Collection API

A REST API service for managing a book collection, built with TypeScript, Express, and SQLite (via `better-sqlite3`).

## Features

- **POST /books** — Create a new book
- **GET /books** — List all books (supports `?author=` filter)
- **GET /books/{id}** — Get a single book by ID
- **PUT /books/{id}** — Update a book (full or partial update)
- **DELETE /books/{id}** — Delete a book
- **GET /health** — Health check endpoint

## Prerequisites

- Node.js >= 18
- npm

## Setup

```bash
# Install dependencies
npm install

# Build the TypeScript source
npm run build
```

## Running

### Production mode

```bash
npm run build
npm start
```

The server starts on `http://localhost:3000` by default. Override the port with the `PORT` environment variable:

```bash
PORT=8080 npm start
```

### Development mode (with hot reload)

```bash
npm run dev
```

## API Reference

### Book object

| Field   | Type    | Required |
|---------|---------|----------|
| title   | string  | yes      |
| author  | string  | yes      |
| year    | integer | no       |
| isbn    | string  | no       |

### Create a book

```
POST /books
```

**Request body:**

```json
{
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0743273565"
}
```

**Response:** `201 Created`

```json
{
  "id": 1,
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0743273565"
}
```

Returns `400 Bad Request` if `title` or `author` is missing or empty.

### List all books

```
GET /books
GET /books?author=F. Scott Fitzgerald
```

**Response:** `200 OK` — a JSON array of book objects.

### Get a single book

```
GET /books/1
```

**Response:** `200 OK` with the book object, or `404 Not Found` if the book does not exist.

### Update a book

```
PUT /books/1
```

**Request body (all fields optional, partial updates supported):**

```json
{
  "title": "Updated Title"
}
```

**Response:** `200 OK` with the updated book object, or `404 Not Found`.

### Delete a book

```
DELETE /books/1
```

**Response:** `204 No Content` on success, or `404 Not Found`.

### Health check

```
GET /health
```

**Response:** `200 OK`

```json
{
  "status": "ok"
}
```

## Data Storage

Data is stored in a SQLite database file (`books.db` in the working directory by default). The database is created automatically on first run.

## Tests

The project includes integration tests using [Vitest](https://vitest.dev/) and [Supertest](https://github.com/ladjs/supertest). Tests run against an in-memory SQLite database so they don't affect any real data.

```bash
# Run all tests
npm test
```

### Test coverage

- **POST /books** — valid creation, missing title (400), missing author (400), minimal valid input
- **GET /books** — listing all, filtering by author, empty list
- **GET /books/:id** — existing book, non-existent (404), invalid id (400)
- **PUT /books/:id** — full update, partial update, non-existent (404)
- **DELETE /books/:id** — successful deletion, non-existent (404)
- **GET /health** — returns status ok, 404 for unknown routes

## Project Structure

```
.
├── src/
│   ├── app.ts            # Express app factory
│   ├── index.ts          # Server entry point
│   ├── db.ts             # SQLite database setup
│   ├── validation.ts     # Zod validation schemas
│   └── routes/
│       ├── books.ts      # Book CRUD routes
│       └── health.ts     # Health check route
├── tests/
│   ├── books.test.ts     # Book API integration tests
│   └── health.test.ts    # Health check tests
├── package.json
├── tsconfig.json
└── vitest.config.ts
```
