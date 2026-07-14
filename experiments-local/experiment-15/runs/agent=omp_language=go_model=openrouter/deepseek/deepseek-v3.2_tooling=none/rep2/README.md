# Book Collection REST API

A REST API service for managing a book collection, built with Go and SQLite.

## Features

- **Create books**: POST `/books` with title, author, year, ISBN
- **List books**: GET `/books` with optional author filter (`?author=`)
- **Get single book**: GET `/books/{id}`
- **Update book**: PUT `/books/{id}`
- **Delete book**: DELETE `/books/{id}`
- **Health check**: GET `/health`

## Requirements

- Go 1.21+
- SQLite (embedded via `modernc.org/sqlite`)

## Installation

1. Clone the repository
2. Build the application:
   ```bash
   go build -o bookapi .
   ```

## Running the API

```bash
# Default port 8080
./bookapi

# Or specify a custom port
PORT=3000 ./bookapi
```

The API will be available at `http://localhost:8080`

## API Endpoints

### Create a Book
```http
POST /books
Content-Type: application/json

{
  "title": "The Go Programming Language",
  "author": "Alan A. A. Donovan",
  "year": 2015,
  "isbn": "978-0134190440"
}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "The Go Programming Language",
  "author": "Alan A. A. Donovan",
  "year": 2015,
  "isbn": "978-0134190440",
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z"
}
```

### List All Books
```http
GET /books
```

**Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "The Go Programming Language",
    "author": "Alan A. A. Donovan",
    "year": 2015,
    "isbn": "978-0134190440",
    "created_at": "2024-01-01T10:00:00Z",
    "updated_at": "2024-01-01T10:00:00Z"
  }
]
```

### Filter Books by Author
```http
GET /books?author=Alan
```

### Get a Single Book
```http
GET /books/{id}
```

### Update a Book
```http
PUT /books/{id}
Content-Type: application/json

{
  "title": "The Go Programming Language (Updated)",
  "author": "Alan A. A. Donovan",
  "year": 2016,
  "isbn": "978-0134190440"
}
```

### Delete a Book
```http
DELETE /books/{id}
```

### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "ok"
}
```

## Data Validation

- **Title**: Required, non-empty string
- **Author**: Required, non-empty string
- **Year**: Optional, must be between 0 and 2100
- **ISBN**: Optional string

## Database

- Uses SQLite with database file `books.db`
- Automatically creates the database and tables on first run
- Includes indexes for efficient querying

## Testing

Run the test suite:

```bash
go test ./test
```

Tests include:
- Health check endpoint
- Create book with validation
- List books
- Get single book
- Update book
- Delete book
- Error cases (missing fields, not found)

## Project Structure

```
├── main.go              # Application entry point
├── models/
│   └── book.go         # Data models and interfaces
├── database/
│   ├── database.go     # Database initialization
│   └── book_store.go   # Database operations
├── handlers/
│   └── handlers.go     # HTTP request handlers
├── test/
│   └── handlers_test.go # Unit tests
└── README.md           # This file
```

## Dependencies

- [Chi](https://github.com/go-chi/chi) - HTTP router
- [modernc.org/sqlite](https://modernc.org/sqlite) - Pure-Go SQLite driver
- [validator](https://github.com/go-playground/validator) - Input validation
- [testify](https://github.com/stretchr/testify) - Testing utilities

## License

MIT