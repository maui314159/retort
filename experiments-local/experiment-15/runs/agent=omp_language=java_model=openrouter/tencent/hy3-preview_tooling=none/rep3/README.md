# Book API

A REST API service for managing a book collection, built with Java and Spring Boot, using SQLite as the embedded database.

## Features

- **POST /books** - Create a new book (title, author, year, isbn)
- **GET /books** - List all books (supports `?author=` filter)
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update a book
- **DELETE /books/{id}** - Delete a book
- **GET /health** - Health check endpoint

## Prerequisites

- Java 17 or higher
- Maven 3.6 or higher

## Setup and Run

### 1. Clone or navigate to the project directory

```bash
cd /var/folders/t6/p1v727892_qc9xqqdzq2rpym0000gn/T/retort-local-gn_2_lea/retort-93c9481ee173
```

### 2. Build the project

```bash
mvn clean install
```

### 3. Run the application

```bash
mvn spring-boot:run
```

The application will start on `http://localhost:8080`

### 4. Run tests

```bash
mvn test
```

## API Usage Examples

### Create a book

```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0743273565"
  }'
```

### List all books

```bash
curl http://localhost:8080/books
```

### Filter books by author

```bash
curl "http://localhost:8080/books?author=Scott"
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
    "title": "Updated Title",
    "author": "Updated Author",
    "year": 2023,
    "isbn": "978-1234567890"
  }'
```

### Delete a book

```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health check

```bash
curl http://localhost:8080/health
```

## Input Validation

- `title` is required
- `author` is required
- `year` and `isbn` are optional

## Database

The application uses SQLite as an embedded database. The database file (`books.db`) will be created automatically in the project root directory when the application starts.

## Response Status Codes

- `200 OK` - Request successful
- `201 Created` - Book created successfully
- `204 No Content` - Book deleted successfully
- `400 Bad Request` - Validation error
- `404 Not Found` - Book not found
