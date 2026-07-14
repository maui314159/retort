# Book API

A REST API service for managing a book collection, built with **Spring Boot 3** and **SQLite**.

## Requirements

- Java 17+ (built and tested on JDK 17–26)
- Maven 3.6+

## Setup & Run

```bash
# from the project root
mvn spring-boot:run
```

The service starts on `http://localhost:8080`. A SQLite database file `books.db`
is created in the working directory on first run; the schema is initialized
automatically via `src/main/resources/schema.sql`.

## Build

```bash
mvn clean package        # produces target/book-api-0.0.1-SNAPSHOT.jar
java -jar target/book-api-0.0.1-SNAPSHOT.jar
```

## Tests

```bash
mvn test
```

Tests run against an in-memory SQLite database (`jdbc:sqlite::memory:`), so
they are fully isolated and require no external setup.

## API Endpoints

| Method   | Path           | Description                              | Success | Not found / invalid |
|----------|----------------|------------------------------------------|---------|---------------------|
| `POST`   | `/books`       | Create a new book                        | `201`   | `400` on validation failure |
| `GET`    | `/books`       | List all books; `?author=` filter        | `200`   | — |
| `GET`    | `/books/{id}`  | Get a single book                        | `200`   | `404` |
| `PUT`    | `/books/{id}`  | Update a book                            | `200`   | `404` / `400` |
| `DELETE` | `/books/{id}`  | Delete a book                            | `204`   | `404` |
| `GET`    | `/health`      | Health check                             | `200`   | — |

### Book fields

| Field   | Type    | Required | Notes                       |
|---------|---------|----------|-----------------------------|
| `title` | string  | yes      | non-blank                   |
| `author`| string  | yes      | non-blank                   |
| `year`  | integer | no       | non-negative if provided    |
| `isbn`  | string  | no       |                             |

`id` is assigned by the database and returned in responses.

### Examples

```bash
# Create
curl -s -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937,"isbn":"978-0261103283"}'

# List all
curl -s http://localhost:8080/books

# Filter by author
curl -s 'http://localhost:8080/books?author=J.R.R.%20Tolkien'

# Get one
curl -s http://localhost:8080/books/1

# Update
curl -s -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1938,"isbn":"978-0261103283"}'

# Delete
curl -s -X DELETE http://localhost:8080/books/1

# Health
curl -s http://localhost:8080/health
```

### Validation errors

A `400` response returns a JSON body of the form:

```json
{ "errors": [ { "field": "title", "message": "title is required" } ] }
```

## Project Layout

```
src/main/java/com/example/bookapi/
├── BookApiApplication.java          # Spring Boot entry point
├── controller/
│   ├── BookController.java          # CRUD endpoints + validation handling
│   └── HealthController.java        # GET /health
├── dto/
│   └── BookRequest.java             # validated request body
├── model/
│   └── Book.java                    # persisted book record
└── repository/
    └── BookRepository.java          # JDBC data access

src/main/resources/
├── application.properties           # SQLite datasource, schema init
└── schema.sql                       # CREATE TABLE IF NOT EXISTS books (...)

src/test/java/com/example/bookapi/
└── BookApiIntegrationTests.java     # 9 end-to-end tests covering all endpoints
src/test/resources/
└── application.properties           # in-memory SQLite for tests
```
