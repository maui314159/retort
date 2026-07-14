# Book Collection API

A REST API service for managing a book collection, built with TypeScript and Express.

## Features

- Create, read, update, and delete books
- Filter books by author
- Input validation for required fields
- Health check endpoint
- SQLite database (in-memory for development/testing)

## Prerequisites

- Node.js (v18 or higher)
- npm (v8 or higher)

## Installation

1. Clone the repository or navigate to the project directory
2. Install dependencies:

```bash
npm install
```

## Building

Compile the TypeScript code:

```bash
npm run build
```

This will create the compiled JavaScript files in the `dist/` directory.

## Running the Server

### Development Mode (with auto-reload)

```bash
npm run dev
```

The server will start on port 3000 (or the port specified in the `PORT` environment variable).

### Production Mode

```bash
npm start
```

## API Endpoints

### Health Check
- `GET /health` - Check API health status

### Books
- `POST /books` - Create a new book
- `GET /books` - List all books (supports `?author=` filter)
- `GET /books/:id` - Get a single book by ID
- `PUT /books/:id` - Update a book
- `DELETE /books/:id` - Delete a book

## Request/Response Examples

### Create a Book

```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0743273565"
  }'
```

Response (201 Created):
```json
{
  "id": 1,
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0743273565",
  "created_at": "2024-01-01T00:00:00.000Z",
  "updated_at": "2024-01-01T00:00:00.000Z"
}
```

### List All Books

```bash
curl http://localhost:3000/books
```

### Filter Books by Author

```bash
curl "http://localhost:3000/books?author=Fitzgerald"
```

### Get a Book by ID

```bash
curl http://localhost:3000/books/1
```

### Update a Book

```bash
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby - Updated Edition"
  }'
```

### Delete a Book

```bash
curl -X DELETE http://localhost:3000/books/1
```

Response (204 No Content)

## Input Validation

- `title` (required for create, optional for update)
- `author` (required for create, optional for update)
- `year` (optional, must be between 0 and current year)
- `isbn` (optional, must match ISBN format)

## Running Tests

```bash
npm test
```

This will run the Jest test suite with 18 integration tests covering all API endpoints.

## Project Structure

```
src/
  ├── index.ts           # Main server entry point
  ├── models/
  │   ├── Book.ts       # Book type definitions
  │   └── database.ts   # Database operations
  ├── routes/
  │   └── bookRoutes.ts # API route handlers
  └── tests/
      └── bookApi.test.ts # Integration tests
```

## Technologies Used

- TypeScript
- Express.js
- better-sqlite3 (SQLite database)
- Jest & Supertest (testing)
- ts-jest (TypeScript testing support)
