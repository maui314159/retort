# Book Collection API

A simple REST API for managing a book collection, built with Rust, Axum, and SQLite.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/books` | Create a new book |
| GET | `/books` | List all books (optional `?author=` filter) |
| GET | `/books/{id}` | Get a single book |
| PUT | `/books/{id}` | Update a book |
| DELETE | `/books/{id}` | Delete a book |

A book has the following fields:
- `title` (required)
- `author` (required)
- `year` (optional)
- `isbn` (optional)

## Build & Run

```bash
cargo build --release
cargo run
```

The server listens on `0.0.0.0:3000` by default. Set `PORT` to change the port, or `DATABASE` to use a persistent SQLite file instead of an in-memory database:

```bash
PORT=8080 DATABASE=books.sqlite cargo run
```

## Example usage

Create a book:

```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Rust Book","author":"Rust Team","year":2023,"isbn":"123-456"}'
```

List books:

```bash
curl http://localhost:3000/books
```

Filter by author:

```bash
curl "http://localhost:3000/books?author=Rust+Team"
```

## Test

```bash
cargo test
```
