# Bookstore REST API

A REST API service for managing a book collection built with Spring Boot and SQLite.

## Features

- **Create a new book** - POST /books
- **List all books** - GET /books (with optional author filter)
- **Get a single book** - GET /books/{id}
- **Update a book** - PUT /books/{id}
- **Delete a book** - DELETE /books/{id}
- **Health check** - GET /health
- **Input validation** - Required fields validated
- **SQLite database** - Embedded database for data storage

## Technology Stack

- Java 25
- Spring Boot 3.4.3
- Spring Data JPA
- SQLite database
- Maven
- JUnit 5

## Prerequisites

- Java 25 or later
- Maven 3.6 or later

## Getting Started

### 1. Clone the repository

```bash
git clone <repository-url>
cd bookstore
```

### 2. Build the project

```bash
mvn clean compile
```

### 3. Run the application

```bash
mvn spring-boot:run
```

The application will start on `http://localhost:8080`.

### 4. Run tests

```bash
mvn test
```

## API Endpoints

### POST /books
Create a new book.

**Request body:**
```json
{
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "9780743273565"
}
```

**Response:**
- `201 Created` with the created book in the body
- `400 Bad Request` if validation fails (title and author are required)

### GET /books
List all books. Supports optional author filter.

**Query parameters:**
- `author` (optional): Filter books by author

**Examples:**
- `GET /books` - returns all books
- `GET /books?author=F.+Scott+Fitzgerald` - returns books by this author

**Response:** `200 OK` with array of books.

### GET /books/{id}
Get a single book by ID.

**Path parameters:**
- `id`: Book ID

**Response:**
- `200 OK` with the book in the body
- `404 Not Found` if book doesn't exist

### PUT /books/{id}
Update a book.

**Path parameters:**
- `id`: Book ID

**Request body:** Same as POST /books

**Response:**
- `200 OK` with the updated book in the body
- `404 Not Found` if book doesn't exist
- `400 Bad Request` if validation fails

### DELETE /books/{id}
Delete a book.

**Path parameters:**
- `id`: Book ID

**Response:**
- `204 No Content` on successful deletion
- `404 Not Found` if book doesn't exist

### GET /health
Health check endpoint.

**Response:** `200 OK` with "OK" in the body.

## Database

The application uses SQLite as an embedded database. The database file `books.db` is created automatically in the project root directory when the application starts.

### Schema

The `books` table has the following columns:
- `id` (autoincrement primary key)
- `title` (required)
- `author` (required)
- `year` (required)
- `isbn`

## Testing

The project includes integration tests covering all endpoints:
- Create and retrieve book
- Get all books
- Filter books by author
- Update book
- Delete book
- Health endpoint
- Input validation

Run tests with:
```bash
mvn test
```

## Project Structure

```
src/main/java/com/example/bookstore/
├── BookstoreApplication.java          # Main application class
├── config/
│   └── SQLiteDialect.java            # Custom SQLite dialect
├── controller/
│   ├── BookController.java           # Book REST endpoints
│   └── HealthController.java         # Health endpoint
├── model/
│   └── Book.java                     # Book entity class
└── repository/
    └── BookRepository.java           # JPA repository

src/test/java/com/example/bookstore/
└── BookControllerIntegrationTest.java # Integration tests
```

## Troubleshooting

### Database Issues

If you encounter database connection issues:
1. Check that the SQLite JDBC driver is in the classpath
2. Verify the `books.db` file is not locked by another process
3. Delete `books.db` to start with a fresh database

### Port Already in Use

If port 8080 is already in use, change the port in `src/main/resources/application.properties`:
```
server.port=8081
```

## License

This project is for demonstration purposes.