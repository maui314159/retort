# Book Collection API

A REST API service for managing a book collection, built with Rust, Actix Web, and SQLite.

## Endpoints

| Method  | Path          | Description                  |
|---------|---------------|------------------------------|
| GET     | /health       | Health check                 |
| POST    | /books        | Create a new book            |
| GET     | /books        | List all books               |
| GET     | /books/{id}   | Get a book by ID             |
| PUT     | /books/{id}   | Update a book                |
| DELETE  | /books/{id}   | Delete a book                |

### Query Parameters

- `GET /books?author=<name>` — Filter books by author

### Book Fields

| Field  | Type   | Required | Description         |
|--------|--------|----------|---------------------|
| title  | string | yes      | Book title          |
| author | string | yes      | Book author         |
| year   | int    | no       | Publication year    |
| isbn   | string | no       | ISBN identifier     |

## Setup

### Prerequisites

- Rust 1.70+ (install via [rustup](https://rustup.rs))

### Build & Run

```bash
# Build
cargo build --release

# Run
cargo run --release
```

The server starts on `http://127.0.0.1:8080`. A `books.db` SQLite file is created automatically in the working directory.

### Run Tests

```bash
cargo test
```

## Usage Examples

```bash
# Health check
curl http://127.0.0.1:8080/health

# Create a book
curl -X POST http://127.0.0.1:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Rust Book","author":"Steve Klabnik","year":2019,"isbn":"978-1-59327-813-4"}'

# List all books
curl http://127.0.0.1:8080/books

# Filter by author
curl "http://127.0.0.1:8080/books?author=Steve%20Klabnik"

# Get a book by ID
curl http://127.0.0.1:8080/books/<id>

# Update a book
curl -X PUT http://127.0.0.1:8080/books/<id> \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated Title","year":2024}'

# Delete a book
curl -X DELETE http://127.0.0.1:8080/books/<id>
```

## HTTP Status Codes

| Code | Meaning                          |
|------|----------------------------------|
| 200  | Success (GET, PUT)               |
| 201  | Created (POST)                   |
| 204  | No Content (DELETE)              |
| 400  | Bad Request (validation failure) |
| 404  | Not Found                        |
| 500  | Internal Server Error            |
