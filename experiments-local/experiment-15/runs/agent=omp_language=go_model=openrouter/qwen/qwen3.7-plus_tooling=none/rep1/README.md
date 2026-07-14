# Book Collection REST API

A REST API service for managing a book collection, built with Go and SQLite.

## Features

- **POST /books** — Create a new book (requires `title` and `author`; optional `year` and `isbn`)
- **GET /books** — List all books (supports `?author=` query parameter for filtering)
- **GET /books/{id}** — Get a single book by ID
- **PUT /books/{id}** — Update a book
- **DELETE /books/{id}** — Delete a book
- **GET /health** — Health check endpoint

## Requirements

- Go 1.22 or higher (uses native method+path routing in `http.ServeMux`)

## Setup and Run

1. Initialize the module and download dependencies (if not already done):
   ```bash
   go mod tidy
   ```

2. Run the server:
   ```bash
   go run main.go
   ```
   The server will start on `http://localhost:8080` and create a local `books.db` SQLite database file.

## Testing

Run the test suite using:
```bash
go test -v ./...
```

## Example Usage

### Create a book
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Go Programming Language", "author": "Alan Donovan", "year": 2015, "isbn": "978-0134190440"}'
```

### List all books
```bash
curl http://localhost:8080/books
```

### Filter books by author
```bash
curl "http://localhost:8080/books?author=Donovan"
```

### Get a single book
```bash
curl http://localhost:8080/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Go Programming Language (2nd Ed)", "author": "Alan Donovan", "year": 2023, "isbn": "978-0134190440"}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health check
```bash
curl http://localhost:8080/health
```
