# Book Collection API

A REST API for managing a book collection, built with Rust, Axum, and SQLite.

## Setup

```bash
# Build
cargo build

# Run
cargo run
```

The server starts on `http://0.0.0.0:3000`. A `books.db` SQLite file is created automatically.

## API Endpoints

| Method  | Path         | Description              |
|---------|--------------|--------------------------|
| GET     | /health      | Health check             |
| POST    | /books       | Create a new book        |
| GET     | /books       | List all books           |
| GET     | /books/{id}  | Get a book by ID         |
| PUT     | /books/{id}  | Update a book            |
| DELETE  | /books/{id}  | Delete a book            |

### Query Parameters

- `GET /books?author=<name>` — Filter books by author

### Request Bodies

**Create book** (`POST /books`):
```json
{
  "title": "The Hobbit",
  "author": "J.R.R. Tolkien",
  "year": 1937,
  "isbn": "978-0261102217"
}
```

`title` and `author` are required. `year` and `isbn` are optional.

**Update book** (`PUT /books/{id}`):
```json
{
  "title": "New Title"
}
```

All fields optional; only provided fields are updated. `title` and `author` cannot be set to empty.

### Status Codes

- `200` — Success (get, update, list)
- `201` — Created
- `204` — Deleted (no content)
- `400` — Validation error
- `404` — Book not found
- `500` — Server error

## Testing

```bash
cargo test
```

## Example Usage

```bash
# Health check
curl http://localhost:3000/health

# Create a book
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

# List all books
curl http://localhost:3000/books

# Filter by author
curl "http://localhost:3000/books?author=Frank%20Herbert"

# Get a book
curl http://localhost:3000/books/1

# Update a book
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"year":1966}'

# Delete a book
curl -X DELETE http://localhost:3000/books/1
```
