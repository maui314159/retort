# Book Collection REST API

A simple RESTful API for managing a personal book collection, built with Java Spring Boot and SQLite.

## Prerequisites
- Java 17 or higher
- Maven 3.8 or higher

## Project Structure
```
.
├── pom.xml                     # Maven project configuration
├── src/
│   ├── main/
│   │   ├── java/com/bookcollection/
│   │   │   ├── BookCollectionApplication.java  # Main application entry point
│   │   │   ├── controller/
│   │   │   │   ├── BookController.java         # CRUD endpoints for books
│   │   │   │   └── HealthController.java       # Health check endpoint
│   │   │   ├── exception/
│   │   │   │   ├── GlobalExceptionHandler.java # Handles 404/400 errors
│   │   │   │   └── ResourceNotFoundException.java
│   │   │   ├── model/
│   │   │   │   └── Book.java                  # JPA entity for books
│   │   │   └── repository/
│   │   │       └── BookRepository.java         # JPA repository interface
│   │   └── resources/
│   │       └── application.properties           # SQLite and JPA config
│   └── test/
│       └── java/com/bookcollection/controller/
│           └── BookControllerTest.java          # Unit/integration tests
└── README.md                  # This file
```

## Run the Application
1. Navigate to the project root directory
2. Start the application with Maven:
```bash
mvn spring-boot:run
```
The API will be available at `http://localhost:8080`.

## API Endpoints

### Health Check
| Method | Endpoint  | Description                  |
|--------|------------|------------------------------|
| GET    | `/health`  | Check application health status |

### Book Management
| Method | Endpoint          | Description                                      |
|--------|-------------------|--------------------------------------------------|
| POST   | `/books`          | Create a new book (requires `title` and `author`) |
| GET    | `/books`          | List all books (supports `?author=` filter)      |
| GET    | `/books/{id}`     | Get a single book by its ID                       |
| PUT    | `/books/{id}`     | Update an existing book by ID                     |
| DELETE | `/books/{id}`     | Delete a book by ID                               |

## Example Requests

### Create a Book
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "9780743273565"}'
```

### List All Books
```bash
curl http://localhost:8080/books
```

### Filter Books by Author
```bash
curl "http://localhost:8080/books?author=F. Scott Fitzgerald"
```

### Get a Book by ID
```bash
curl http://localhost:8080/books/1
```

### Update a Book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby (Revised)", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "9780743273565"}'
```

### Delete a Book
```bash
curl -X DELETE http://localhost:8080/books/1
```

## Run Tests
Execute the following Maven command to run all unit/integration tests:
```bash
mvn test
```

## Validation Rules
- `title` and `author` are required fields (requests missing these will return `400 Bad Request`)
- `year` and `isbn` are optional fields
- Invalid requests return JSON error messages with appropriate HTTP status codes