# Book Collection REST API

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

1. Clone the repository or download the source files
2. Navigate to the project directory
3. Install dependencies:

```bash
go mod download
```

## Build

To build the executable:

```bash
go build -o book-api .
```

## Run

### Direct Execution

```bash
go run .
```

The server will start on port 8080 by default.

### Custom Port

To use a different port, set the `PORT` environment variable:

```bash
PORT=3000 go run .
```

## API Documentation

### Health Check

**GET /health**

Returns the API health status.

Response:
```json
{
  "status": "healthy",
  "time": "2024-01-01T00:00:00Z"
}
```

### Create a Book

**POST /books**

Request body:
```json
{
  "title": "The Go Programming Language",
  "author": "Alan A. A. Donovan",
  "year": 2015,
  "isbn": "978-0134190440"
}
```

Response (201 Created):
```json
{
  "id": 1,
  "title": "The Go Programming Language",
  "author": "Alan A. A. Donovan",
  "year": 2015,
  "isbn": "978-0134190440",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### List Books

**GET /books** - List all books

**GET /books?author={author}** - Filter by author (partial match)

Response (200 OK):
```json
[
  {
    "id": 1,
    "title": "The Go Programming Language",
    "author": "Alan A. A. Donovan",
    "year": 2015,
    "isbn": "978-0134190440",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

### Get a Book

**GET /books/{id}**

Response (200 OK):
```json
{
  "id": 1,
  "title": "The Go Programming Language",
  "author": "Alan A. A. Donovan",
  "year": 2015,
  "isbn": "978-0134190440",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Update a Book

**PUT /books/{id}**

Request body (all fields optional):
```json
{
  "title": "Updated Title",
  "year": 2024
}
```

Response (200 OK):
```json
{
  "id": 1,
  "title": "Updated Title",
  "author": "Alan A. A. Donovan",
  "year": 2024,
  "isbn": "978-0134190440",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

### Delete a Book

**DELETE /books/{id}**

Response (204 No Content)

## Input Validation

- `title` and `author` are required for creating a book
- Both fields must contain only printable ASCII characters
- `title` must not exceed 500 characters
- `author` must not exceed 200 characters

## Run Tests

To run the test suite:

```bash
go test -v ./...
```

The test suite includes:
1. Health check endpoint test
2. Create and get book test
3. List books with filter test
4. Update book test
5. Delete book test
6. Input validation test
7. Book not found test

## Database

The API uses SQLite for data storage. By default, it creates a file named `books.db` in the current directory. You can modify the database path in `main.go`.

For testing, an in-memory SQLite database is used.

## Error Responses

All error responses return JSON in the format:

```json
{
  "error": "Error message here"
}
```

HTTP status codes used:
- 200 OK - Successful GET/PUT request
- 201 Created - Successful POST request
- 204 No Content - Successful DELETE request
- 400 Bad Request - Invalid input or request body
- 404 Not Found - Book not found
- 405 Method Not Allowed - Invalid HTTP method
- 500 Internal Server Error - Server error
