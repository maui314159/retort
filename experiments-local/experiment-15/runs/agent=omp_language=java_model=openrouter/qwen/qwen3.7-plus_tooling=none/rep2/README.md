# Book Collection REST API

A REST API service for managing a book collection, built with Java, Spring Boot, and SQLite.

## Requirements
- Java 17 or higher
- Maven 3.6+

## Setup and Run Instructions

1. Clone the repository and navigate to the project directory.
2. Build the project using Maven:
   ```bash
   mvn clean install
   ```
3. Run the application:
   ```bash
   mvn spring-boot:run
   ```
   Alternatively, you can run the packaged JAR:
   ```bash
   java -jar target/book-api-0.0.1-SNAPSHOT.jar
   ```

## API Endpoints

- `GET /health` - Health check endpoint
- `POST /books` - Create a new book
- `GET /books` - List all books (supports `?author=` filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book

### Example Requests

**Create a book:**
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}'
```

**Get all books:**
```bash
curl http://localhost:8080/books
```

**Filter books by author:**
```bash
curl "http://localhost:8080/books?author=Orwell"
```

## Tests

Run the tests using Maven:
```bash
mvn test
```