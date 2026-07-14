# Book Collection REST API

A simple REST API service for managing a book collection built with Go and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Input validation (title and author required)
- Health check endpoint
- SQLite database for data storage

## Requirements

- Go 1.16 or higher

## Installation

1. Clone the repository
2. Install dependencies:

```bash
go mod download
```

## Running the Application

Start the server:

```bash
go run cmd/bookapi/main.go
```

The server will start on port 8080.

## API Endpoints

### Health Check
```
GET /health
```
Returns the service health status.

### List Books
```
GET /books
```
Returns all books. Supports optional author filter:
```
GET /books?author=Hemingway
```

### Get Single Book
```
GET /books/{id}
```
Returns a specific book by ID.

### Create Book
```
POST /books
```
Creates a new book. Request body must be JSON:

```json
{
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0743273565"
}
```

**Note:** `title` and `author` are required fields.

### Update Book
```
PUT /books/{id}
```
Updates an existing book. Request body format same as create.

### Delete Book
```
DELETE /books/{id}
```
Deletes a book by ID.

## Testing

Run the test suite:

```bash
go test ./...
```

## Project Structure

```
.
├── cmd/
│   └── bookapi/
│       └── main.go          # Application entry point
├── internal/
│   ├── db/
│   │   ├── database.go      # Database initialization
│   │   └── book_repository.go # Database operations
│   ├── handlers/
│   │   └── book_handler.go  # HTTP request handlers
│   ├── health/
│   │   └── handler.go       # Health check handler
│   └── models/
│       └── book.go          # Data model
├── go.mod                   # Go module definition
├── go.sum                   # Dependency checksums
└── README.md                # This file
```

## Database

The application uses SQLite with a database file named `books.db` in the current directory. The database is automatically created and initialized when the application starts.

## Example Usage

```bash
# Start the server
go run cmd/bookapi/main.go

# Create a book
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}'

# List all books
curl http://localhost:8080/books

# Filter by author
curl http://localhost:8080/books?author=Orwell

# Get a specific book
curl http://localhost:8080/books/1

# Update a book
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}'

# Delete a book
curl -X DELETE http://localhost:8080/books/1

# Health check
curl http://localhost:8080/health
```