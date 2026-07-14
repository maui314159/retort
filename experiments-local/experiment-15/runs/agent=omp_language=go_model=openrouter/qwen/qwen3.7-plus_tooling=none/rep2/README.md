# Book Collection REST API

A REST API service for managing a book collection, built with Go, Chi router, and SQLite.

## Requirements

- Go 1.21+

## Setup

1. Clone or navigate to the project directory.
2. Download dependencies:
   ```bash
   go mod tidy
   ```

## Running the Server

Start the server with the default in-file SQLite database (`books.db`):
```bash
go run .
```

To use a custom database file path, set the `DB_PATH` environment variable:
```bash
DB_PATH=/path/to/custom.db go run .
```

The server will start and listen on `http://localhost:8080`.

## API Endpoints

### Health Check
- **GET** `/health`
  - Returns `{"status": "healthy"}` with a `200 OK` status.

### Books

- **POST** `/books`
  - Creates a new book.
  - **Request Body:** `{"title": "string", "author": "string", "year": int, "isbn": "string"}`
  - **Validation:** `title` and `author` are required.
  - **Response:** `201 Created` with the created book object (including generated `id`).

- **GET** `/books`
  - Lists all books.
  - **Query Params:** `?author=<partial_name>` (optional filter, case-insensitive partial match).
  - **Response:** `200 OK` with an array of book objects.

- **GET** `/books/{id}`
  - Retrieves a single book by its ID.
  - **Response:** `200 OK` with the book object, or `404 Not Found`.

- **PUT** `/books/{id}`
  - Updates an existing book.
  - **Request Body:** `{"title": "string", "author": "string", "year": int, "isbn": "string"}`
  - **Validation:** `title` and `author` are required.
  - **Response:** `200 OK` with the updated book object, or `404 Not Found`.

- **DELETE** `/books/{id}`
  - Deletes a book by its ID.
  - **Response:** `204 No Content` on success, or `404 Not Found`.

## Testing

Run the test suite:
```bash
go test -v ./...
```

The tests use an in-memory SQLite database to ensure isolation and fast execution.

## Example Usage

```bash
# Create a book
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}'

# List all books
curl http://localhost:8080/books

# Filter books by author
curl "http://localhost:8080/books?author=Orwell"

# Get a specific book (replace 1 with actual ID)
curl http://localhost:8080/books/1

# Update a book
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Nineteen Eighty-Four", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}'

# Delete a book
curl -X DELETE http://localhost:8080/books/1
```
