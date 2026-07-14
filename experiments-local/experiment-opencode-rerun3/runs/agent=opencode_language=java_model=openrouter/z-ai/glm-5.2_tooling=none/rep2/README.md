# Books API

A REST API service for managing a book collection, built with Spring Boot and SQLite.

## Requirements

- Java 17+ (built/tested on Java 26)
- Maven

## Setup & Run

```bash
mvn clean package
java -jar target/books-api-0.0.1-SNAPSHOT.jar
```

Or run directly:

```bash
mvn spring-boot:run
```

The server starts on `http://localhost:8080`. A SQLite database file `books.db`
is created automatically in the working directory on first run.

## Endpoints

| Method | Path           | Description                          |
|--------|----------------|--------------------------------------|
| GET    | `/health`      | Health check                         |
| POST   | `/books`       | Create a new book                    |
| GET    | `/books`       | List all books (`?author=` optional) |
| GET    | `/books/{id}`  | Get a single book by ID              |
| PUT    | `/books/{id}`  | Update a book                        |
| DELETE | `/books/{id}`  | Delete a book                        |

### Book JSON shape

```json
{
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "978-0441172719"
}
```

`title` and `author` are required; `year` and `isbn` are optional.

## Status Codes

- `200 OK` — successful GET/PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — validation failure (returns field error messages)
- `404 Not Found` — book not found

## Examples

```bash
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'

curl 'http://localhost:8080/books?author=Frank%20Herbert'
curl http://localhost:8080/books/1
curl -X DELETE http://localhost:8080/books/1
```

## Tests

```bash
mvn test
```

Tests include:
- `BooksApiApplicationTests` — context loads, schema initialization
- `BookServiceTests` — service-layer CRUD and filter behavior
- `BookControllerIntegrationTests` — full HTTP flow via MockMvc (health, create,
  validation, filter, get/update/delete, status codes)
