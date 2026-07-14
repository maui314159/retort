# Book Collection REST API

A Spring Boot REST API for managing a book collection with SQLite database.

## Requirements

- Java 17 or higher
- Maven 3.6 or higher

## Setup and Run Instructions

### 1. Build the application

```bash
mvn clean package
```

### 2. Run the application

```bash
mvn spring-boot:run
```

The application will start on port 8080.

### 3. API Endpoints

#### Health Check
```
GET /health
```
Returns: `Service is healthy`

#### Books Collection

- **GET /books** - List all books
  - Query parameter: `?author=` (optional) - Filter by author name
  - Example: `GET http://localhost:8080/books?author=Fitzgerald`

- **GET /books/{id}** - Get a single book by ID
  - Example: `GET http://localhost:8080/books/1`

- **POST /books** - Create a new book
  - Request body (JSON):
    ```json
    {
      "title": "The Great Gatsby",
      "author": "F. Scott Fitzgerald",
      "year": 1925,
      "isbn": "9780743273565"
    }
    ```
  - Required fields: `title`, `author`, `year`
  - Optional field: `isbn`

- **PUT /books/{id}** - Update a book
  - Example: `PUT http://localhost:8080/books/1`
  - Request body: Same as POST

- **DELETE /books/{id}** - Delete a book
  - Example: `DELETE http://localhost:8080/books/1`

### 4. Validation Rules

- Title: Required, cannot be blank
- Author: Required, cannot be blank
- Year: Required, must be a valid year
- ISBN: Optional, must be unique if provided

### 5. Database

The application uses SQLite with an embedded database file `books.db` that will be created automatically in the working directory.

### 6. Running Tests

```bash
mvn test
```

The test suite includes:
- Unit tests for service layer
- Integration tests for REST controllers
- Health check endpoint test

## Project Structure

```
src/main/java/com/example/bookapi/
├── BookApiApplication.java           # Main application class
├── controller/
│   ├── BookController.java           # REST endpoints for books
│   └── HealthController.java         # Health check endpoint
├── dto/
│   └── BookDTO.java                  # Data Transfer Object
├── entity/
│   └── Book.java                     # JPA entity
├── exception/
│   └── GlobalExceptionHandler.java   # Global exception handling
├── repository/
│   └── BookRepository.java           # JPA repository
└── service/
    └── BookService.java              # Business logic
```

## Example Requests

### Create a book
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "1984",
    "author": "George Orwell",
    "year": 1949,
    "isbn": "9780451524935"
  }'
```

### List all books
```bash
curl http://localhost:8080/books
```

### Filter books by author
```bash
curl "http://localhost:8080/books?author=Orwell"
```

### Get a specific book
```bash
curl http://localhost:8080/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "1984",
    "author": "George Orwell",
    "year": 1949,
    "isbn": "9780451524935"
  }'
```

### Delete a book
```bash
curl -X DELETE http://localhost:8080/books/1
```