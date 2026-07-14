# Book Collection REST API

A TypeScript/Express REST API for managing a book collection, backed by SQLite.

## Features

- `POST /books` — Create a new book (title, author, year, isbn)
- `GET /books` — List all books (supports `?author=` filter)
- `GET /books/{id}` — Get a single book by ID
- `PUT /books/{id}` — Update a book
- `DELETE /books/{id}` — Delete a book
- `GET /health` — Health check

Input validation ensures `title` and `author` are non-empty strings.

## Setup

Install dependencies:

```bash
npm install
```

## Run

Development (with hot reload):

```bash
npm run dev
```

Production build and start:

```bash
npm run build
npm start
```

The server listens on port `3000` by default. Set `PORT` to override:

```bash
PORT=8080 npm start
```

## Test

```bash
npm test
```

## Example usage

```bash
# Create a book
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937,"isbn":"978-0547928227"}'

# List books
curl http://localhost:3000/books

# Filter by author
curl "http://localhost:3000/books?author=J.R.R.%20Tolkien"

# Get a book
curl http://localhost:3000/books/1

# Update a book
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Hobbit, or There and Back Again","author":"J.R.R. Tolkien","year":1937}'

# Delete a book
curl -X DELETE http://localhost:3000/books/1

# Health check
curl http://localhost:3000/health
```
