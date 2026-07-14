# Books API

A REST API service for managing a book collection, built with TypeScript, Express, and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Input validation
- Health check endpoint
- SQLite persistence

## Prerequisites

- Node.js 18+
- npm

## Setup

Install dependencies:

```bash
npm install
```

## Running the Server

Development mode with `ts-node`:

```bash
npm run dev
```

Production build and start:

```bash
npm run build
npm start
```

The server runs on port `3000` by default. Set the `PORT` environment variable to override.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/books` | Create a new book |
| GET | `/books` | List all books (optional `?author=` filter) |
| GET | `/books/:id` | Get a single book |
| PUT | `/books/:id` | Update a book |
| DELETE | `/books/:id` | Delete a book |

### Example Requests

Create a book:

```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937, "isbn": "978-0547928227"}'
```

List books:

```bash
curl http://localhost:3000/books
```

Filter by author:

```bash
curl "http://localhost:3000/books?author=Tolkien"
```

Get a single book:

```bash
curl http://localhost:3000/books/1
```

Update a book:

```bash
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Lord of the Rings"}'
```

Delete a book:

```bash
curl -X DELETE http://localhost:3000/books/1
```

## Testing

Run the test suite:

```bash
npm test
```

Tests use an in-memory SQLite database and cover health checks, CRUD operations, validation, and filtering.
