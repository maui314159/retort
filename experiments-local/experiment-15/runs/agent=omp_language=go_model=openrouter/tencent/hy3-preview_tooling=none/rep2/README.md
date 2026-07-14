# Book Collection REST API

A simple REST API service for managing a book collection, built with Go and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Input validation (title and author are required)
- SQLite database for persistent storage
- Health check endpoint

## API Endpoints

| Method | Endpoint | Description |
|--------|-----------|-------------|
| POST | `/books` | Create a new book |
| GET | `/books` | List all books (supports `?author=` filter) |
| GET | `/books/{id}` | Get a single book by ID |
| PUT | `/books/{id}` | Update a book |
| DELETE | `/books/{id}` | Delete a book |
| GET | `/health` | Health check |

## Book Object

```json
{
  "id": 1,
  "title": "The Go Programming Language",
  "author": "Alan Donovan",
  "year": 2015,
  "isbn": "978-0134190440",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

## Setup and Run

### Prerequisites

- Go 1.21 or later

### Installation

1. Clone or download the source code
2. Navigate to the project directory
3. Install dependencies:

```bash
go mod tidy
```

### Running the Server

```bash
go run .
```

The server will start on `http://localhost:8080`

### Building the Binary

```bash
go build -o bookapi .
./bookapi
```

## Usage Examples

### Create a Book

```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}'
```

### List All Books

```bash
curl http://localhost:8080/books
```

### Filter Books by Author

```bash
curl "http://localhost:8080/books?author=Orwell"
```

### Get a Specific Book

```bash
curl http://localhost:8080/books/1
```

### Update a Book

```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "1984 (Updated Edition)"}'
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
go test -v ./...
```

## Project Structure

```
.
├── main.go      # Application entry point and HTTP router
├── models.go    # Data structures and request/response types
├── storage.go   # SQLite database operations
├── handlers.go  # HTTP request handlers
├── main_test.go # Unit and integration tests
├── go.mod       # Go module file
└── README.md    # This file
```

## Database

The application uses SQLite and creates a `books.db` file in the current directory. The database schema is created automatically on first run.

## License

MIT
