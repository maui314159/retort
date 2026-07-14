# Books API

A REST API service for managing a book collection, built with **Spring Boot 3** and **SQLite** (embedded).

## Features

- `POST /books` — Create a new book (`title`, `author`, `year`, `isbn`)
- `GET /books` — List all books (supports `?author=` filter)
- `GET /books/{id}` — Get a single book by ID
- `PUT /books/{id}` — Update a book
- `DELETE /books/{id}` — Delete a book
- `GET /health` — Health check endpoint

`title` and `author` are required and validated. Responses are JSON with
appropriate HTTP status codes (`201 Created`, `200 OK`, `204 No Content`,
`400 Bad Request`, `404 Not Found`, `500 Internal Server Error`).

## Prerequisites

- Java 17+ (built/tested with JDK 26)
- Maven 3.6+ (or use the included Maven wrapper via `./mvnw`)

## Setup & Run

From the project directory:

```bash
./mvnw spring-boot:run
# or, if Maven is installed globally:
mvn spring-boot:run
```

The service starts on `http://localhost:8080`. A SQLite database file
`books.db` is created in the working directory on first run (the schema is
initialized automatically).

## Build

```bash
mvn clean package
```

Produces `target/books-api-1.0.0.jar`, which can be run with:

```bash
java -jar target/books-api-1.0.0.jar
```

## Tests

```bash
mvn test
```

Integration tests use MockMvc against an in-memory SQLite database and cover
create/read/update/delete, author filtering, validation errors, 404 handling,
and the health check.

## Example Usage

```bash
# Create a book
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

# List all books
curl http://localhost:8080/books

# Filter by author
curl "http://localhost:8080/books?author=Frank%20Herbert"

# Get one book
curl http://localhost:8080/books/1

# Update a book
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Dune Updated","author":"Frank Herbert","year":1965}'

# Delete a book
curl -X DELETE http://localhost:8080/books/1

# Health check
curl http://localhost:8080/health
```

## Project Structure

```
src/main/java/com/example/books/
  BooksApplication.java          # Spring Boot entry point
  SchemaInitializer.java         # Initializes SQLite schema on startup
  controller/BookController.java # CRUD endpoints for /books
  controller/HealthController.java # GET /health
  exception/GlobalExceptionHandler.java # JSON error responses
  model/Book.java                # Book model with validation
  repository/BookRepository.java # JDBC-based persistence
src/main/resources/application.properties
src/test/java/com/example/books/BookApiIntegrationTests.java
```

## Configuration

The database URL and pool settings are configured in
`src/main/resources/application.properties`. Override via environment
variables or command-line arguments, e.g.:

```bash
spring.datasource.url=jdbc:sqlite:/var/data/books.db
```
