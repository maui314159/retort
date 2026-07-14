# Book Collection REST API

A Rust-based REST API for managing a book collection using Actix-web and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Input validation
- Health check endpoint
- JSON responses with appropriate HTTP status codes

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/books` | Create a new book |
| GET | `/books` | List all books (supports `?author=` filter) |
| GET | `/books/{id}` | Get a single book by ID |
| PUT | `/books/{id}` | Update a book |
| DELETE | `/books/{id}` | Delete a book |

## Book Model

```json
{
  "title": "string (required)",
  "author": "string (required)",
  "year": "integer (optional)",
  "isbn": "string (optional)"
}
```

## Setup

### Prerequisites

- Rust (latest stable version)
- Cargo

### Installation

1. Clone the repository or navigate to the project directory

2. Build the project:
```bash
cargo build --release
```

3. Run the server:
```bash
cargo run
```

The server will start at `http://127.0.0.1:8080`

### Environment Variables

- `DATABASE_URL`: SQLite database URL (default: `sqlite:books.db`)

## Usage Examples

### Create a book

```bash
curl -X POST http://127.0.0.1:8080/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Rust Programming Language",
    "author": "Steve Klabnik",
    "year": 2018,
    "isbn": "978-1718503106"
  }'
```

### List all books

```bash
curl http://127.0.0.1:8080/books
```

### Filter books by author

```bash
curl "http://127.0.0.1:8080/books?author=Klabnik"
```

### Get a specific book

```bash
curl http://127.0.0.1:8080/books/1
```

### Update a book

```bash
curl -X PUT http://127.0.0.1:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated Title"
  }'
```

### Delete a book

```bash
curl -X DELETE http://127.0.0.1:8080/books/1
```

### Health check

```bash
curl http://127.0.0.1:8080/health
```

## Running Tests

```bash
cargo test
```

## Project Structure

```
├── Cargo.toml          # Project dependencies
├── src/
│   ├── main.rs         # Application entry point
│   ├── models.rs       # Data models and validation
│   ├── db.rs           # Database operations
│   └── handlers.rs     # HTTP request handlers
└── README.md           # This file
```
