# Book Collection REST API

A REST API service for managing a book collection, built with Rust, Axum, and SQLite.

## Features

- **POST /books** — Create a new book (requires `title` and `author`, optional `year` and `isbn`)
- **GET /books** — List all books (supports `?author=` filter for partial name matching)
- **GET /books/{id}** — Get a single book by UUID
- **PUT /books/{id}** — Update a book (partial updates supported)
- **DELETE /books/{id}** — Delete a book
- **GET /health** — Health check endpoint returning "OK"

## Technical Stack

- **Framework**: Axum (0.7)
- **Database**: SQLite (via SQLx)
- **Async Runtime**: Tokio
- **Serialization**: Serde / Serde JSON
- **Identifiers**: UUID v4

## Setup and Run Instructions

1. Ensure you have Rust and Cargo installed.
2. Clone the repository and navigate to the project directory.
3. Build the project:
   ```bash
   cargo build --release
   ```
4. Run the server:
   ```bash
   cargo run
   ```
   The server will start on `http://0.0.0.0:3000`.

## API Examples

### Create a Book
```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Rust Programming Language", "author": "Steve Klabnik", "year": 2019, "isbn": "978-1718500440"}'
```

### List All Books
```bash
curl http://localhost:3000/books
```

### List Books by Author (Partial Match)
```bash
curl "http://localhost:3000/books?author=Steve"
```

### Get a Single Book
```bash
curl http://localhost:3000/books/<uuid>
```

### Update a Book
```bash
curl -X PUT http://localhost:3000/books/<uuid> \
  -H "Content-Type: application/json" \
  -d '{"year": 2020}'
```

### Delete a Book
```bash
curl -X DELETE http://localhost:3000/books/<uuid>
```

### Health Check
```bash
curl http://localhost:3000/health
```

## Testing

Run the integration test suite:
```bash
cargo test
```

The tests use an in-memory SQLite database to ensure isolation and speed.
