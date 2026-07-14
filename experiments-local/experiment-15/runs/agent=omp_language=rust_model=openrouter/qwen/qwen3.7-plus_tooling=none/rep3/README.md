# Book Collection API

A REST API service for managing a book collection, built with Rust, Axum, and SQLite.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (supports `?author=` query parameter for filtering)
- **GET /books/{id}** — Get a single book by ID
- **PUT /books/{id}** — Update a book
- **DELETE /books/{id}** — Delete a book
- **GET /health** — Health check endpoint

## Technical Constraints

- Built with Axum web framework
- Data stored in SQLite (`books.db`)
- Returns JSON responses with appropriate HTTP status codes
- Includes input validation (title and author are required)

## Setup and Run Instructions

### Prerequisites

- Rust (1.75+) installed via [rustup](https://rustup.rs/)

### Installation

1. Clone the repository (or navigate to the project directory).
2. Build the project:
   ```bash
   cargo build
   ```

### Running the Server

Start the server in development mode:
```bash
cargo run
```
The server will start on `http://127.0.0.1:8080`.

### Running Tests

Execute the test suite:
```bash
cargo test
```

## API Examples

### Create a Book
```bash
curl -X POST http://127.0.0.1:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Rust Programming Language", "author": "Steve Klabnik", "year": 2018, "isbn": "978-1718500440"}'
```

### List All Books
```bash
curl http://127.0.0.1:8080/books
```

### List Books by Author
```bash
curl "http://127.0.0.1:8080/books?author=Klabnik"
```

### Get a Book by ID
```bash
curl http://127.0.0.1:8080/books/<book-id>
```

### Update a Book
```bash
curl -X PUT http://127.0.0.1:8080/books/<book-id> \
  -H "Content-Type: application/json" \
  -d '{"year": 2019}'
```

### Delete a Book
```bash
curl -X DELETE http://127.0.0.1:8080/books/<book-id>
```

### Health Check
```bash
curl http://127.0.0.1:8080/health
```