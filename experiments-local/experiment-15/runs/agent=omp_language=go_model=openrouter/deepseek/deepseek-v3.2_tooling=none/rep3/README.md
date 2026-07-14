# Book Collection REST API

A simple REST API service for managing a book collection, built with Go, SQLite, and Gorilla Mux.

## Features

- **Create** a new book with title, author, year, and ISBN
- **List** all books with optional author filter
- **Get** a single book by ID
- **Update** an existing book
- **Delete** a book by ID
- **Health check** endpoint
- Input validation (title and author required)
- SQLite embedded database

## Requirements

- Go 1.26+
- SQLite driver (installed automatically)

## Installation & Running

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd bookapi
   ```

2. Install dependencies:
   ```bash
   go mod download
   ```

3. Run the application:
   ```bash
   go run main.go
   ```

   The server will start on `http://localhost:8080`.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/books` | Create a new book |
| `GET`  | `/books` | List all books (supports `?author=name` filter) |
| `GET`  | `/books/{id}` | Get a book by ID |
| `PUT`  | `/books/{id}` | Update a book |
| `DELETE` | `/books/{id}` | Delete a book |
| `GET`  | `/health` | Health check |

### Request/Response Examples

#### Create a Book

**Request**
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Go Programming Language",
    "author": "Alan A. A. Donovan",
    "year": 2015,
    "isbn": "978-0134190440"
  }'
```

**Response**
```json
{
  "id": 1
}
```

#### List All Books

**Request**
```bash
curl http://localhost:8080/books
```

**Response**
```json
[
  {
    "id": 1,
    "title": "The Go Programming Language",
    "author": "Alan A. A. Donovan",
    "year": 2015,
    "isbn": "978-0134190440"
  }
]
```

#### Filter by Author

**Request**
```bash
curl http://localhost:8080/books?author=Alan%20A.%20A.%20Donovan
```

#### Get a Single Book

**Request**
```bash
curl http://localhost:8080/books/1
```

#### Update a Book

**Request**
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Go Programming Language (2nd Edition)",
    "author": "Alan A. A. Donovan",
    "year": 2021,
    "isbn": "978-0134190440"
  }'
```

**Response**: `204 No Content`

#### Delete a Book

**Request**
```bash
curl -X DELETE http://localhost:8080/books/1
```

**Response**: `204 No Content`

#### Health Check

**Request**
```bash
curl http://localhost:8080/health
```

**Response**
```json
{
  "status": "healthy"
}
```

## Project Structure

```
.
├── main.go                 # Application entry point
├── go.mod                  # Go module definition
├── README.md               # This file
├── handlers/               # HTTP handlers
│   ├── handlers.go         # Route registration
│   ├── book.go             # Book CRUD handlers
│   ├── health.go           # Health check handler
│   └── handlers_test.go    # Integration tests
├── models/                 # Data models
│   └── book.go             # Book struct
├── repository/             # Data access layer
│   ├── book_repository.go  # Repository interface
│   └── sqlite_book_repository.go # SQLite implementation
└── database/               # Database setup
    └── setup.go            # SQLite initialization
```

## Running Tests

```bash
go test ./handlers -v
```

Tests run with an in‑memory SQLite database and cover all endpoints.

## Validation Rules

- **Title** and **author** are required (non‑empty strings)
- **Year** is optional (integer)
- **ISBN** is optional (string)
- Invalid requests return `400 Bad Request`

## Error Handling

- `400 Bad Request` – Invalid input or malformed JSON
- `404 Not Found` – Book with given ID does not exist
- `500 Internal Server Error` – Database or server error

## License

MIT