# Book API Service

A REST API service for managing a book collection, built with Go and SQLite.

## Features

- **POST /books** - Create a new book (title, author, year, isbn)
- **GET /books** - List all books (supports `?author=` filter)
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update a book
- **DELETE /books/{id}** - Delete a book
- **GET /health** - Health check endpoint

## Prerequisites

- Go 1.21 or later

## Setup

1. Clone or download this directory
2. Install dependencies:
   ```bash
   go mod download
   ```

## Running the Server

```bash
go run main.go
```

The server will start on `http://localhost:8080`

## API Usage

### Create a Book
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"1984","author":"George Orwell","year":1949,"isbn":"9780451524935"}'
```

### List All Books
```bash
curl http://localhost:8080/books
```

### Filter Books by Author
```bash
curl "http://localhost:8080/books?author=Orwell"
```

### Get a Book by ID
```bash
curl http://localhost:8080/books/1
```

### Update a Book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"1984 (Updated)","author":"George Orwell","year":1950,"isbn":"9780451524936"}'
```

### Delete a Book
```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health Check
```bash
curl http://localhost:8080/health
```

## Running Tests

```bash
go test -v
```

This will run all unit and integration tests.

## Input Validation

- `title` is required
- `author` is required
- `year` and `isbn` are optional

## Database

The service uses SQLite (via `modernc.org/sqlite`) as an embedded database. The database file is stored at `./books.db` in the current directory.

## Response Format

All responses are in JSON format. Successful operations return the relevant data with appropriate HTTP status codes:

- `200 OK` - Successful GET/PUT
- `201 Created` - Successful POST
- `204 No Content` - Successful DELETE
- `400 Bad Request` - Invalid input
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

## Example Book JSON

```json
{
  "id": 1,
  "title": "1984",
  "author": "George Orwell",
  "year": 1949,
  "isbn": "9780451524935"
}
```
