# Book Collection REST API

A REST API for managing a book collection, built with Spring Boot and H2 (embedded database).

## Prerequisites

- Java 17+
- Maven 3.8+

## Setup & Run

```bash
# Build
mvn clean package

# Run
java -jar target/book-api-0.0.1-SNAPSHOT.jar

# Or run with Maven
mvn spring-boot:run
```

The server starts on `http://localhost:8080`.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/books` | Create a new book |
| `GET` | `/books` | List all books |
| `GET` | `/books/{id}` | Get a book by ID |
| `PUT` | `/books/{id}` | Update a book |
| `DELETE` | `/books/{id}` | Delete a book |

### Query Parameters

- `GET /books?author=<name>` — Filter books by author

### Book Fields

| Field | Type | Required |
|-------|------|----------|
| `title` | string | Yes |
| `author` | string | Yes |
| `year` | integer | No |
| `isbn` | string | No |

## Examples

```bash
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
  -d '{"title":"1984","author":"George Orwell","year":1949,"isbn":"978-0441013593"}'

# Delete a book
curl -X DELETE http://localhost:8080/books/1

# Health check
curl http://localhost:8080/health
```

## Run Tests

```bash
mvn test
```
