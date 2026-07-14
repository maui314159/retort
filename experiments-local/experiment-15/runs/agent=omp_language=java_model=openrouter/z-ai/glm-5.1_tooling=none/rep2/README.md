# Book Collection API

A REST API for managing a book collection, built with Spring Boot, Spring Data JPA, and H2.

## Prerequisites

- Java 17+
- Maven 3.6+

## Setup & Run

```bash
mvn clean package
java -jar target/book-collection-1.0.0.jar
```

The server starts on `http://localhost:8080`.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/books` | Create a new book |
| GET | `/books` | List all books (supports `?author=` filter) |
| GET | `/books/{id}` | Get a book by ID |
| PUT | `/books/{id}` | Update a book |
| DELETE | `/books/{id}` | Delete a book |
| GET | `/health` | Health check |

### Create a Book

```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'
```

Returns `201 Created` with the created book (including generated `id`).

### List Books

```bash
curl http://localhost:8080/books
curl "http://localhost:8080/books?author=Frank+Herbert"
```

### Get a Book

```bash
curl http://localhost:8080/books/1
```

Returns `404 Not Found` if the book doesn't exist.

### Update a Book

```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Dune Messiah"}'
```

Only included fields are updated; omitted fields remain unchanged.

### Delete a Book

```bash
curl -X DELETE http://localhost:8080/books/1
```

Returns `204 No Content` on success, `404 Not Found` if the book doesn't exist.

### Health Check

```bash
curl http://localhost:8080/health
```

Returns `{"status":"UP"}`.

## Input Validation

- `title` — required (non-blank)
- `author` — required (non-blank)
- `year` — optional integer
- `isbn` — optional string

Invalid input returns `400 Bad Request` with error details.

## Data Storage

Uses H2 file-based database (`books.db` in the working directory). Data persists across restarts.

## Running Tests

```bash
mvn test
```
