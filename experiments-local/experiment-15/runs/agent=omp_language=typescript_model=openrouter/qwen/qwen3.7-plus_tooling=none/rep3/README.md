# Book Collection API

A REST API service for managing a book collection, built with TypeScript, Express, and SQLite.

## Features

- **POST /books** — Create a new book
- **GET /books** — List all books (supports `?author=` filter)
- **GET /books/{id}** — Get a single book by ID
- **PUT /books/{id}** — Update a book
- **DELETE /books/{id}** — Delete a book
- **GET /health** — Health check endpoint

## Technical Stack

- **Runtime:** Node.js
- **Language:** TypeScript
- **Web Framework:** Express
- **Database:** SQLite (embedded, uses `:memory:` in test environment)
- **Testing:** Jest + Supertest

## Setup and Run Instructions

### Prerequisites

- Node.js (v18 or higher recommended)
- `bun` or `npm`

### Installation

1. Install dependencies:
   ```bash
   bun install
   # or: npm install
   ```

2. Build the TypeScript code:
   ```bash
   bun run build
   # or: npm run build
   ```

### Running the Server

Start the production server:
```bash
bun run start
# or: npm run start
```
The server will start on `http://localhost:3000` (or the port specified in the `PORT` environment variable).

### Development Mode

For hot-reloading during development (requires `ts-node`):
```bash
bun run dev
# or: npm run dev
```

### Running Tests

Execute the test suite:
```bash
bun run test
# or: npm run test
```

## API Examples

### Health Check
```bash
curl http://localhost:3000/health
```

### Create a Book
```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Pragmatic Programmer", "author": "Andrew Hunt", "year": 1999, "isbn": "978-0201616224"}'
```

### List All Books
```bash
curl http://localhost:3000/books
```

### List Books by Author
```bash
curl "http://localhost:3000/books?author=Andrew%20Hunt"
```

### Get a Book by ID
```bash
curl http://localhost:3000/books/1
```

### Update a Book
```bash
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Pragmatic Programmer, 20th Anniversary Edition"}'
```

### Delete a Book
```bash
curl -X DELETE http://localhost:3000/books/1
```

## Validation

- `title` and `author` are required for creating a book.
- Missing required fields will return a `400 Bad Request`.
- Attempting to access, update, or delete a non-existent book returns `404 Not Found`.