# Bookstore REST API

A small REST API for managing a book collection, built with **Spring Boot 3** and **SQLite**.

## Endpoints

| Method   | Path          | Description                          |
|----------|---------------|--------------------------------------|
| `GET`    | `/health`     | Health check                         |
| `POST`   | `/books`      | Create a book (title, author, year, isbn) |
| `GET`    | `/books`      | List all books (optional `?author=` filter) |
| `GET`    | `/books/{id}` | Get a single book by ID              |
| `PUT`    | `/books/{id}` | Update a book                        |
| `DELETE` | `/books/{id}` | Delete a book                        |

`title` and `author` are required. Validation errors return `400 Bad Request`
with a JSON body describing the failing fields. Missing books return `404`.

## Status codes

- `200 OK` — successful read / update
- `201 Created` — book created (response body includes the new `id`)
- `204 No Content` — book deleted
- `400 Bad Request` — validation failure
- `404 Not Found` — book not found

## Prerequisites

- JDK 17+ (built and tested on JDK 26)
- Maven 3.6+

## Setup & run

```bash
mvn clean package
java -jar target/bookstore-1.0.0.jar
```

The service starts on `http://localhost:8080`. SQLite data is stored in
`books.db` in the working directory (created automatically on first run).

### Run without packaging

```bash
mvn spring-boot:run
```

## Run the tests

```bash
mvn test
```

Tests use an in-memory SQLite database (`jdbc:sqlite:file::memory:?cache=shared`)
and exercise every endpoint plus validation and error paths.

## Example

```bash
# Create a book
curl -s -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"1984","author":"George Orwell","year":1949,"isbn":"978-0451524935"}'

# List all books
curl -s http://localhost:8080/books

# Filter by author
curl -s 'http://localhost:8080/books?author=George%20Orwell'

# Get / update / delete
curl -s http://localhost:8080/books/1
curl -s -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"1984","author":"George Orwell","year":1950,"isbn":"978-0451524935"}'
curl -s -X DELETE http://localhost:8080/books/1
```

## Project layout

```
src/main/java/com/example/bookstore/
  BookstoreApplication.java          # entry point
  model/Book.java                    # domain model + validation constraints
  repository/BookRepository.java     # JDBC data access
  controller/BookController.java     # REST endpoints
  controller/HealthController.java   # /health
  controller/BookNotFoundException.java
  controller/GlobalExceptionHandler.java
src/main/resources/
  application.properties
  schema.sql                         # books table
src/test/java/com/example/bookstore/
  BookControllerTest.java            # MockMvc integration tests
```
