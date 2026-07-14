# Book Collection API

A REST API for managing a book collection, built with Rust, Axum, and SQLite.

## Setup

```bash
# Build
cargo build

# Run
cargo run
# Server starts on http://localhost:3000
```

## Endpoints

| Method | Path         | Description               |
|--------|--------------|---------------------------|
| GET    | /health      | Health check              |
| POST   | /books       | Create a book             |
| GET    | /books       | List books (?author=filter) |
| GET    | /books/{id}  | Get a book by ID          |
| PUT    | /books/{id}  | Update a book             |
| DELETE | /books/{id}  | Delete a book             |

## Example

```bash
# Create
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Rust Book","author":"Steve","year":2024}'

# List all
curl http://localhost:3000/books

# Filter by author
curl 'http://localhost:3000/books?author=Steve'

# Get one
curl http://localhost:3000/books/<id>

# Update
curl -X PUT http://localhost:3000/books/<id> \
  -H 'Content-Type: application/json' \
  -d '{"title":"New Title"}'

# Delete
curl -X DELETE http://localhost:3000/books/<id>
```

## Validation

- `title` and `author` are required when creating a book.
- Empty strings are rejected for `title` and `author`.

## Tests

```bash
cargo test
```
