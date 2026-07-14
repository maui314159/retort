# Book API

A REST API service for managing a book collection, built with Rust using Actix-web and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- Input validation
- SQLite database

## Endpoints

- `POST /books` - Create a new book
- `GET /books` - List all books (supports `?author=` filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

## Setup

### Prerequisites

- Rust (edition 2021 or later)
- Cargo

### Installation

1. Clone or download the source code
2. Navigate to the project directory
3. Build the project:

```bash
cargo build --release
```

## Running the Service

### Development mode

```bash
cargo run
```

### Production mode

```bash
cargo run --release
```

### Custom database location

By default, the service uses `sqlite:book_collection.db`. To use a different database:

```bash
export DATABASE_URL="sqlite:/path/to/database.db"
cargo run
```

## API Examples

### Create a book

```bash
curl -X POST <http://localhost:8080/books> \\
  -H "Content-Type: application/json" \\
  -d '{
    "title": "The Rust Programming Language",
    "author": "Steve Klabnik",
    "year": 2018,
    "isbn": "978-1718500440"
  }'
```

### List all books

```bash
curl <http://localhost:8080/books>
```

### Filter books by author

```bash
curl "<http://localhost:8080/books?author=Steve>"
```

### Get a specific book

```bash
curl <http://localhost:8080/books/{id}>
```

### Update a book

```bash
curl -X PUT <http://localhost:8080/books/{id}> \\
  -H "Content-Type: application/json" \\
  -d '{
    "title": "Updated Title"
  }'
```

### Delete a book

```bash
curl -X DELETE <http://localhost:8080/books/{id}>
```

### Health check

```bash
curl <http://localhost:8080/health>
```

## Running Tests

```bash
cargo test
```

## Project Structure

```
src/
  main.rs   - Entry point, route configuration
  handlers.rs - HTTP request handlers
  models.rs  - Data models and request/response types
  db.rs      - Database operations
```

## Dependencies

- actix-web - Web framework
- sqlx - Async SQLite driver
- serde - Serialization/deserialization
- validator - Input validation
- chrono - Date/time handling
- uuid - Unique ID generation
