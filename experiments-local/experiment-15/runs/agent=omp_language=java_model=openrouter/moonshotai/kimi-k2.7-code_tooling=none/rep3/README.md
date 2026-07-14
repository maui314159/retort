# Books REST API

A small Spring Boot REST API for managing a book collection backed by an embedded SQLite database.

## Requirements

- Java 17 or later
- Apache Maven 3.6+

## Build

```bash
mvn clean package
```

## Run

```bash
mvn spring-boot:run
```

The application starts on port `8080` and stores data in `books.db`.

## API

### Health check

```bash
curl http://localhost:8080/health
```

### Create a book

```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"Clean Code","author":"Robert C. Martin","year":2008,"isbn":"9780132350884"}'
```

### List all books

```bash
curl http://localhost:8080/books
```

### Filter by author

```bash
curl "http://localhost:8080/books?author=Martin"
```

### Get a single book

```bash
curl http://localhost:8080/books/1
```

### Update a book

```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Clean Code","author":"Robert C. Martin","year":2008,"isbn":"9780132350884"}'
```

### Delete a book

```bash
curl -X DELETE http://localhost:8080/books/1
```

## Tests

```bash
mvn test
```

The test suite includes unit tests for validation and integration tests covering the full CRUD lifecycle.
