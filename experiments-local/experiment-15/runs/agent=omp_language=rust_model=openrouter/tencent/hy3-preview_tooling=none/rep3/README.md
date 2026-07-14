# Book Manager REST API

A simple REST API service for managing a book collection, built with Rust using Actix-web and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Input validation
- Health check endpoint
- SQLite database for persistence

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
  "id": 1,
  "title": "The Rust Programming Language",
  "author": "Steve Klabnik",
  "year": 2023,
  "isbn": "978-1718503106"
}
```

## Setup and Run

### Prerequisites

- Rust (latest stable version)
- Cargo

### Installation

1. Clone or navigate to the project directory
2. Build the project:
   ```bash
   cargo build
   ```

### Running the Server

```bash
cargo run
```

The server will start on `http://127.0.0.1:8080`

### Running Tests

```bash
cargo test
```

## API Examples

### Create a book

```bash
curl -X POST http://127.0.0.1:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}'
```

### List all books

```bash
curl http://127.0.0.1:8080/books
```

### Filter books by author

```bash
curl "http://127.0.0.1:8080/books?author=George%20Orwell"
```

### Get a specific book

```bash
curl http://127.0.0.1:8080/books/1
```

### Update a book

```bash
curl -X PUT http://127.0.0.1:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "1984 (Updated Edition)"}'
```

### Delete a book

```bash
curl -X DELETE http://127.0.0.1:8080/books/1
```

### Health check

```bash
curl http://127.0.0.1:8080/health
```

## Input Validation

- `title` and `author` are required fields
- `title` and `author` cannot be empty strings
- `year` and `isbn` are optional

## Database

The application uses SQLite for data persistence. A file named `books.db` will be created in the current directory when the server starts.
