# Book Collection REST API

A simple REST API for managing a book collection, built with Java 17 and Spring Boot, using SQLite as the embedded database.

## Prerequisites
- Java 17 or higher
- Maven 3.6 or higher

## Setup and Run
1. Navigate to the project directory (current working directory)
2. Build the project (downloads dependencies and compiles code):
   ```bash
   mvn clean install
   ```
3. Run the application:
   ```bash
   mvn spring-boot:run
   ```
The application will start on port 8080 by default.

## API Endpoints
| Method | Endpoint | Description | Request Body | Response |
|--------|-----------|-------------|--------------|-----------|
| POST | `/books` | Create a new book | `{"title": "string", "author": "string", "year": integer, "isbn": "string"}` | 201 Created with book data |
| GET | `/books` | List all books (supports `?author=` filter) | None | 200 OK with array of books |
| GET | `/books/{id}` | Get a single book by ID | None | 200 OK with book data, 404 if not found |
| PUT | `/books/{id}` | Update a book | `{"title": "string", "author": "string", "year": integer, "isbn": "string"}` | 200 OK with updated book data, 404 if not found |
| DELETE | `/books/{id}` | Delete a book | None | 204 No Content, 404 if not found |
| GET | `/health` | Health check | None | 200 OK with "UP" |

## Input Validation
- `title` and `author` are required for POST and PUT requests. If missing, the API returns 400 Bad Request.

## Running Tests
Run all unit and integration tests with:
```bash
mvn test
```

## Example Requests
### Create a book
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937, "isbn": "978-0547928227"}'
```

### List all books
```bash
curl http://localhost:8080/books
```

### Filter books by author
```bash
curl "http://localhost:8080/books?author=Tolkien"
```

### Get a book by ID
```bash
curl http://localhost:8080/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Hobbit: An Unexpected Journey", "author": "J.R.R. Tolkien"}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health check
```bash
curl http://localhost:8080/health
```
