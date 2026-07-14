# Book Collection REST API

A simple REST API service for managing a book collection, built with Go and SQLite.

## Features

- **POST /books**: Create a new book (requires `title` and `author`).
- **GET /books**: List all books (supports `?author=` query parameter for filtering).
- **GET /books/{id}**: Get a single book by ID.
- **PUT /books/{id}**: Update a book.
- **DELETE /books/{id}**: Delete a book.
- **GET /health**: Health check endpoint.

## Prerequisites

- Go 1.21 or higher

## Setup and Run

1. Initialize the module and download dependencies:
   ```bash
   go mod tidy
   ```

2. Run the application:
   ```bash
   go run main.go
   ```
   The server will start on port `8080` by default. You can change the port by setting the `PORT` environment variable:
   ```bash
   PORT=3000 go run main.go
   ```

3. (Optional) Change the SQLite database path by setting the `DB_PATH` environment variable:
   ```bash
   DB_PATH=/tmp/mybooks.db go run main.go
   ```

## Testing

Run the unit and integration tests:
```bash
go test -v
```

## Example Usage

### Create a Book
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Go Programming Language", "author": "Alan A. A. Donovan", "year": 2015, "isbn": "978-0134190440"}'
```

### List Books
```bash
curl http://localhost:8080/books
```

### Filter Books by Author
```bash
curl "http://localhost:8080/books?author=Donovan"
```

### Get a Book by ID
```bash
curl http://localhost:8080/books/1
```

### Update a Book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Go Programming Language", "author": "Alan A. A. Donovan", "year": 2016, "isbn": "978-0134190440"}'
```

### Delete a Book
```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health Check
```bash
curl http://localhost:8080/health
```
