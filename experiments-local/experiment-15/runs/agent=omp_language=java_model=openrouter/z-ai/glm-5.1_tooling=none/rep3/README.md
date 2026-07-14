# Book Collection API

A REST API for managing a book collection, built with Spring Boot and H2.

## Prerequisites

- Java 17+
- Maven 3.8+

## Setup & Run

```bash
./mvnw spring-boot:run
```

The server starts on `http://localhost:8080`.

## API Endpoints

| Method   | Path         | Description                     |
|----------|--------------|---------------------------------|
| `GET`    | `/health`    | Health check                    |
| `POST`   | `/books`     | Create a new book               |
| `GET`    | `/books`     | List all books (optional `?author=` filter) |
| `GET`    | `/books/{id}`| Get a book by ID                |
| `PUT`    | `/books/{id}`| Update a book                   |
| `DELETE` | `/books/{id}`| Delete a book                   |

## Example Requests

```bash
# Health check
curl http://localhost:8080/health

# Create a book
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"1984","author":"George Orwell","year":1949,"isbn":"978-0451524935"}'

# List all books
curl http://localhost:8080/books

# Filter by author
curl "http://localhost:8080/books?author=George%20Orwell"

# Get a book
curl http://localhost:8080/books/1

# Update a book
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"1984","author":"George Orwell","year":1949,"isbn":"978-0451524935"}'

# Delete a book
curl -X DELETE http://localhost:8080/books/1
```

## Validation

- `title` and `author` are required fields.
- Missing or blank values return `400 Bad Request` with an error message.

## Run Tests

```bash
./mvnw test
```
