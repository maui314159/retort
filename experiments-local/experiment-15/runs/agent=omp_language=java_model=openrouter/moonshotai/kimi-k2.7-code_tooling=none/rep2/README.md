# Book Collection REST API

A Spring Boot REST API for managing a book collection, backed by an embedded H2 database.

## Requirements

- Java 17 or later
- Maven 3.6 or later

## Build

```bash
mvn clean package
```

## Run

```bash
mvn spring-boot:run
```

The application starts on port `8080`.

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/books` | Create a new book |
| GET | `/books` | List all books (optional `?author=` filter) |
| GET | `/books/{id}` | Get a book by ID |
| PUT | `/books/{id}` | Update a book |
| DELETE | `/books/{id}` | Delete a book |

## Example requests

Create a book:

```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937,"isbn":"978-0547928227"}'
```

List books by author:

```bash
curl "http://localhost:8080/books?author=Tolkien"
```

## Test

```bash
mvn test
```
