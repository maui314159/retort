# Book Collection API

A REST API service for managing a book collection, built with TypeScript, Express, Zod, and SQLite (better-sqlite3).

## Requirements

- Node.js 18+
- npm

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Build the project:
   ```bash
   npm run build
   ```

## Running the Application

Start the server:
```bash
npm start
```
The server will run on `http://localhost:3000` (or the port specified in the `PORT` environment variable).

For development with hot reloading, use:
```bash
npm run dev
```

## API Endpoints

### Health Check
- **GET** `/health`
  - Returns: `{ "status": "ok" }`

### Books

- **POST** `/books`
  - Creates a new book.
  - Body: `{ "title": "string", "author": "string", "year": "number", "isbn": "string" }`
  - `title` and `author` are required.
  - Returns: `201 Created` with the new book object including its `id`.

- **GET** `/books`
  - Lists all books.
  - Query (optional): `?author=Name` to filter by author (case-insensitive partial match).
  - Returns: `200 OK` with an array of book objects.

- **GET** `/books/:id`
  - Gets a single book by its ID.
  - Returns: `200 OK` with the book object, or `404 Not Found`.

- **PUT** `/books/:id`
  - Updates an existing book.
  - Body: same as POST.
  - Returns: `200 OK` with the updated book object, or `404 Not Found`.

- **DELETE** `/books/:id`
  - Deletes a book by its ID.
  - Returns: `204 No Content`, or `404 Not Found`.

## Testing

Run the test suite:
```bash
npm test
```

Tests cover health checks, CRUD operations, filtering, and input validation.

## Project Structure

- `src/index.ts` - Express application entry point
- `src/routes.ts` - API route definitions and validation logic
- `src/db.ts` - SQLite database initialization
- `src/index.test.ts` - Integration tests
