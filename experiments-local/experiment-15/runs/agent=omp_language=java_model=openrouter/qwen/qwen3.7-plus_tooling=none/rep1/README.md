# Book Collection REST API

A Spring Boot REST API service for managing a book collection, backed by a SQLite database.

## Requirements

- Java 17 or higher
- Maven 3.6+

## Setup and Run Instructions

1. **Clone or navigate to the project directory:**
   ```bash
   cd /path/to/project
   ```

2. **Build the project:**
   ```bash
   mvn clean install
   ```

3. **Run the application:**
   ```bash
   mvn spring-boot:run
   ```
   The server will start on `http://localhost:8080`. A `books.db` SQLite database file will be created in the project root directory.

## API Endpoints

### Health Check
- `GET /health`
  - Returns `{"status": "UP"}` if the service is running.

### Books Management
- `POST /books`
  - Create a new book.
  - **Body:** `{"title": "string", "author": "string", "year": number, "isbn": "string"}`
  - **Validation:** `title` and `author` are required.
  - **Response:** `201 Created` with the created book.

- `GET /books`
  - List all books.
  - **Query Params:** `?author=<name>` (optional, filters books by author name, case-insensitive).
  - **Response:** `200 OK` with a list of books.

- `GET /books/{id}`
  - Get a single book by its ID.
  - **Response:** `200 OK` with the book, or `404 Not Found`.

- `PUT /books/{id}`
  - Update an existing book.
  - **Body:** `{"title": "string", "author": "string", "year": number, "isbn": "string"}`
  - **Response:** `200 OK` with the updated book, or `404 Not Found`.

- `DELETE /books/{id}`
  - Delete a book by its ID.
  - **Response:** `204 No Content` on success, or `404 Not Found`.

## Running Tests

Execute the integration tests using:
```bash
mvn test
```
Tests run against an in-memory SQLite database to ensure isolation and speed.