# Book Collection API

A REST API service for managing a book collection, built with Express, TypeScript, and SQLite.

## Features

- **POST /books** — Create a new book (`title`, `author`, `year`, `isbn`)
- **GET /books** — List all books (supports `?author=` filter)
- **GET /books/:id** — Get a single book by ID
- **PUT /books/:id** — Update a book
- **DELETE /books/:id** — Delete a book
- **GET /health** — Health check endpoint

## Requirements

- Node.js 18+
- npm or yarn

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Build the TypeScript code:
   ```bash
   npm run build
   ```

## Running the Server

Start the server in production mode:
```bash
npm start
```

For development with hot-reloading:
```bash
npm run dev
```

The server will run on `http://localhost:3000` by default. You can change the port by setting the `PORT` environment variable.

## Testing

Run the test suite:
```bash
npm test
```

## Example Usage

### Create a book
```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937, "isbn": "978-0547928227"}'
```

### List all books
```bash
curl http://localhost:3000/books
```

### Filter by author
```bash
curl "http://localhost:3000/books?author=Tolkien"
```

### Get a single book
```bash
curl http://localhost:3000/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:3000/books/1
```
