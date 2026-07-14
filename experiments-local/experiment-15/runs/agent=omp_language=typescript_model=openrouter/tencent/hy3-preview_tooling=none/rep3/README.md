# Book Collection API

A REST API service for managing a book collection, built with TypeScript, Express, and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Input validation
- Health check endpoint
- SQLite database (in-memory by default)

## API Endpoints

| Method | Endpoint | Description |
|--------|-----------|-------------|
| POST | `/books` | Create a new book |
| GET | `/books` | List all books (supports `?author=` filter) |
| GET | `/books/:id` | Get a single book by ID |
| PUT | `/books/:id` | Update a book |
| DELETE | `/books/:id` | Delete a book |
| GET | `/health` | Health check |

## Book Object

```json
{
  "id": 1,
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "9780743273565"
}
```

## Setup

### Prerequisites

- Node.js 22 or later
- npm

### Installation

1. Clone the repository
2. Install dependencies:

```bash
npm install
```

## Running the Application

### Development Mode

```bash
npm run dev
```

The server will start on port 3000 (or set `PORT` environment variable).

### Production Mode

Build the TypeScript code:

```bash
npm run build
```

Start the server:

```bash
npm start
```

## Running Tests

```bash
npm test
```

This runs the Jest test suite with 13 integration tests covering all API endpoints.

## API Examples

### Create a Book

```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "9780743273565"
  }'
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

### Health Check

```bash
curl http://localhost:3000/health
```

## Input Validation

- `title` and `author` are required fields
- Returns 400 status code if validation fails

## Response Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 204 | No Content (successful delete) |
| 400 | Bad Request (validation error or invalid ID) |
| 404 | Not Found |
| 500 | Internal Server Error |
