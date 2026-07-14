# Book Collection API

A REST API service for managing a book collection, built with Rust, Axum, and SQLite.

## Features

- **Create, Read, Update, Delete** books
- **Filter books by author** via query parameter
- **Input validation** (title and author required)
- **Health check endpoint**
- **SQLite database** with migrations
- **JSON request/responses** with appropriate HTTP status codes
- **Comprehensive error handling**

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/books` | Create a new book |
| `GET` | `/books` | List all books (optional `?author=Name` filter) |
| `GET` | `/books/{id}` | Get a single book by ID |
| `PUT` | `/books/{id}` | Update a book |
| `DELETE` | `/books/{id}` | Delete a book |

## Request/Response Examples

### Create a book

**Request:**
```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Rust Programming Language",
    "author": "Steve Klabnik",
    "year": 2018,
    "isbn": "1593278284"
  }'
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "The Rust Programming Language",
  "author": "Steve Klabnik",
  "year": 2018,
  "isbn": "1593278284"
}
```

### List all books

**Request:**
```bash
curl http://localhost:3000/books
```

**Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "The Rust Programming Language",
    "author": "Steve Klabnik",
    "year": 2018,
    "isbn": "1593278284"
  }
]
```

### Filter books by author

**Request:**
```bash
curl "http://localhost:3000/books?author=Steve%20Klabnik"
```

### Get a book by ID

**Request:**
```bash
curl http://localhost:3000/books/550e8400-e29b-41d4-a716-446655440000
```

### Update a book

**Request:**
```bash
curl -X PUT http://localhost:3000/books/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Rust Programming Language (2nd Edition)",
    "year":行为的n 2022
  }'
```

**Note:** Partial updates are supported. Only include fields you want to change.

### Delete a book

**Request:**
```bash
curl -X DELETE http://localhost:3000/books/550e8400-e29b-41d4-a716-446655440000
```

**Response:** 204 No Content

### Health check

**Request:**
```bash
curl http://localhost:3000/health
```

**Response:**
```json
{
  "status": "ok"
}
```

## Getting Started

### Prerequisites

- [Rust](https://www.rust-lang.org/tools/install) 1.70+
- [SQLx CLI](https://github.com/launchbadge/sqlx/blob/main/sqlx-cli/README.md) (for migrations)

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd book-collection-api
   ```

2. Install dependencies:
   ```bash
   cargo build
   ```

3. Set up the database:
   ```bash
   # Create database and run migrations
   DATABASE_URL=sqlite:books.db cargo sqlx database create
   DATABASE_URL=sqlite:books.db cargo sqlx migrate run
   
   # Prepare SQLx offline queries
   DATABASE_URL=sqlite:books.db cargo sqlx prepare -- --lib
   ```

4. Run the server:
   ```bash
   cargo run
   ```

   The server will start at `http://localhost:3000`.

### Environment Variables

- `DATABASE_URL`: SQLite connection string (default: `sqlite:books.db`)
- `RUST_LOG`: Log level (default: `info`)

### Running Tests

```bash
# Run all tests
cargo test

# Run only unit tests
cargo test --lib

# Run only integration tests
cargo test --test integration
```

## Project Structure

```
.
├── Cargo.toml
├── migrations/
│   └── 20240613000000_create_books.sql
├── src/
│   ├── main.rs              # Application entry point
│   ├── lib.rs               # Library exports
│   ├── db/
│   │   ├── mod.rs           # Database module
│   │   └── repository.rs    # Book repository
│   ├── models.rs            # Data models and validation
│   ├── error.rs             # Error types and handling
│   └── routes/
│       ├── mod.rs           # Routes module
│       ├── health.rs        # Health endpoint
│       └── books.rs         # Book endpoints
└── tests/
    └── integration.rs       # Integration tests
```

## Dependencies

- **axum**: Web framework
- **tokio**: Async runtime
- **sqlx**: Async SQL toolkit
- **serde**: Serialization/deserialization
- **uuid**: UUID generation
- **validator**: Input validation
- **tracing**: Logging

## Error Handling

The API returns appropriate HTTP status codes:

- `200 OK`: Successful request
- `201 Created`: Resource created successfully
- `204 No Content`: Resource deleted successfully
- `400 Bad Request`: Validation error
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

Error responses include a JSON body with an error message:
```json
{
  "error": "Validation error: title: Title is required"
}
```

## Development

### Adding New Endpoints

1. Define request/response models in `src/models.rs`
2. Add repository methods in `src/db/repository.rs` if needed
3. Create route handlers in `src/routes/`
4. Register routes in the router

### Database Migrations

Create a new migration:
```bash
sqlx migrate add <migration_name>
```

## License

MIT