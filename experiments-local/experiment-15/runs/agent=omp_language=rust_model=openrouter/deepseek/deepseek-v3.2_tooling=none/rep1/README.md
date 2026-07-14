# Book Collection REST API

A REST API service for managing a book collection built with Rust and Axum.

## Features

- **POST /books** - Create a new book
- **GET /books** - List all books (with optional author filter)
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update a book
- **DELETE /books/{id}** - Delete a book
- **GET /health** - Health check endpoint

## Requirements

- Rust 1.70 or higher
- SQLite

## Setup

1. Clone the repository
2. Install dependencies:

```bash
cargo build
```

3. Run the server:

```bash
cargo run
```

By default, the server runs on `http://localhost:3000` and uses a SQLite database at `books.db`.

You can override the database URL with the `DATABASE_URL` environment variable:

```bash
DATABASE_URL=sqlite:books.db cargo run
```

## API Documentation

### Create a Book

```http
POST /books
Content-Type: application/json

{
  "title": "The Rust Programming Language",
  "author": "Steve Klabnik",
  "year": 2018,
  "isbn": "978-1593278281"
}
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "The Rust Programming Language",
  "author": "Steve Klabnik",
  "year": 2018,
  "isbn": "978-1593278281",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### List Books

```http
GET /books
```

Optional query parameter:
- `author` - Filter books by author

```http
GET /books?author=Steve%20Klabnik
```

### Get a Book

```http
GET /books/{id}
```

### Update a Book

```http
PUT /books/{id}
Content-Type: application/json

{
  "title": "Updated Title",
  "author": "Updated Author",
  "year": 2023,
  "isbn": "978-0123456789"
}
```

Partial updates are supported.

### Delete a Book

```http
DELETE /books/{id}
```

### Health Check

```http
GET /health
```

Returns "OK" with status 200.

## Validation

- Title and author are required (non-empty)
- Year must be between 1000 and 9999
- ISBN is required (non-empty)
- ISBN must be unique

## Error Handling

All errors return JSON responses with appropriate HTTP status codes:

- `400 Bad Request` - Validation errors
- `404 Not Found` - Book not found
- `409 Conflict` - Duplicate ISBN
- `500 Internal Server Error` - Server errors

## Running Tests

```bash
cargo test
```

## Project Structure

- `src/main.rs` - Application entry point and routing
- `src/error.rs` - Error types and handling
- `src/models.rs` - Data models and validation
- `src/database.rs` - Database connection and migrations
- `src/handlers.rs` - Request handlers
- `migrations/` - SQL migration files
- `tests/` - Integration tests

## Dependencies

- [axum](https://crates.io/crates/axum) - Web framework
- [sqlx](https://crates.io/crates/sqlx) - Async SQL toolkit
- [serde](https://crates.io/crates/serde) - Serialization/deserialization
- [uuid](https://crates.io/crates/uuid) - UUID generation
- [tokio](https://crates.io/crates/tokio) - Async runtime
- [tracing](https://crates.io/crates/tracing) - Structured logging