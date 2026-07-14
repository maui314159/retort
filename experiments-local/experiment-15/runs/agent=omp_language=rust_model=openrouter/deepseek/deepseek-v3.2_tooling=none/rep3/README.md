# Book Collection REST API

A Rust-based REST API service for managing a book collection, built with Axum and SQLite.

## Features

- Create new books (title, author, year, ISBN)
- List all books with optional author filtering
- Get a single book by ID
- Update book details
- Delete books
- Health check endpoint
- Input validation
- SQLite database storage
- JSON responses with appropriate HTTP status codes

## Requirements

- Rust 1.70+
- SQLite

## Getting Started

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd book-api
   ```

2. Build the project:
   ```bash
   cargo build --release
   ```

### Configuration

The application uses environment variables for configuration:

- `DATABASE_URL`: SQLite database URL (default: `sqlite:books.db`)
- `PORT`: Server port (default: `3000`)
- `RUST_LOG`: Logging level (default: `book_api=debug`)

### Running the Application

```bash
# Run with default settings
cargo run

# Or run the release binary
cargo run --release

# With custom database
DATABASE_URL=sqlite:mydb.db cargo run

# With custom port
PORT=8080 cargo run
```

The server will start on `http://localhost:3000` (or the configured port).

## API Endpoints

### Health Check
```
GET /health
```

Response:
```json
{
  "status": "ok"
}
```

### Create a Book
```
POST /books
```

Request body:
```json
{
  "title": "The Rust Programming Language",
  "author": "Steve Klabnik and Carol Nichols",
  "year": 2018,
  "isbn": "978-1593278281"
}
```

**Required fields:** `title`, `author`

### List Books
```
GET /books
```

Optional query parameter:
- `author`: Filter books by author name

Response:
```json
[
  {
    "id": "uuid-string",
    "title": "Book Title",
    "author": "Author Name",
    "year": 2020,
    "isbn": "1234567890",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

### Get a Single Book
```
GET /books/{id}
```

### Update a Book
```
PUT /books/{id}
```

Request body (partial updates supported):
```json
{
  "title": "Updated Title",
  "author": "Updated Author"
}
```

### Delete a Book
```
DELETE /books/{id}
```

## Database Schema

The application uses SQLite with the following schema:

```sql
CREATE TABLE books (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_books_author ON books(author);
```

## Running Tests

```bash
# Run all tests
cargo test

# Run integration tests only
cargo test --test integration
```

## Project Structure

```
book-api/
├── src/
│   ├── main.rs          # Application entry point
│   ├── lib.rs           # Library exports
│   ├── error.rs         # Error types and handling
│   ├── models.rs        # Data models and validation
│   └── handlers.rs      # HTTP request handlers
├── migrations/
│   └── 001_initial.sql  # Database migrations
├── tests/
│   └── integration.rs   # Integration tests
├── Cargo.toml           # Dependencies
└── README.md            # This file
```

## Error Handling

The API returns appropriate HTTP status codes:

- `200 OK`: Successful request
- `201 Created`: Resource created successfully
- `204 No Content`: Resource deleted successfully
- `400 Bad Request`: Invalid input data
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

Error responses include a JSON body with error details:
```json
{
  "error": "Error message",
  "status": 400
}
```

## License

[Your License Here]