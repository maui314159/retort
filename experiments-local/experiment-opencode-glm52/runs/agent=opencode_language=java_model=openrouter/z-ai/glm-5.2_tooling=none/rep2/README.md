# Books API

A REST API service for managing a book collection, built with Spring Boot and SQLite.

## Requirements

- Java 17+ (tested with JDK 26)
- Maven 3.6+

## Setup & Run

```bash
mvn clean package
java -jar target/books-api-0.0.1-SNAPSHOT.jar
```

Or run directly during development:

```bash
mvn spring-boot:run
```

The service starts on `http://localhost:8080`. A SQLite database file `books.db`
is created automatically in the working directory on first run.

## Endpoints

| Method   | Path           | Description                          |
|----------|----------------|--------------------------------------|
| `GET`    | `/health`      | Health check (returns `{"status":"UP"}`) |
| `POST`   | `/books`       | Create a new book                    |
| `GET`    | `/books`       | List all books (supports `?author=`) |
| `GET`    | `/books/{id}`  | Get a single book                    |
| `PUT`    | `/books/{id}`  | Update a book                        |
| `DELETE` | `/books/{id}`  | Delete a book                        |

### Book payload

```json
{
  "title": "The Hobbit",
  "author": "J.R.R. Tolkien",
  "year": 1937,
  "isbn": "978-0261103283"
}
```

`title` and `author` are required. `year` and `isbn` are optional.

### Example

```bash
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937,"isbn":"978-0261103283"}'

curl 'http://localhost:8080/books?author=J.R.R.%20Tolkien'
```

## HTTP status codes

- `200 OK` — successful read/update
- `201 Created` — successful create
- `204 No Content` — successful delete
- `400 Bad Request` — validation failure (returns field error map)
- `404 Not Found` — book not found

## Tests

```bash
mvn test
```

Tests include:
- `HealthControllerTest` — health endpoint returns `UP`.
- `BookControllerIntegrationTest` — full CRUD lifecycle, validation errors, and
  `?author=` filtering against a SQLite-backed Spring context.
- `BookServiceTest` — service-level unit tests with Mockito.
