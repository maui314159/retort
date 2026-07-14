# Book Collection REST API

A Spring Boot REST API for managing a book collection, backed by SQLite.

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/books` | Create a new book |
| GET | `/books` | List all books (optional `?author=` filter) |
| GET | `/books/{id}` | Get a single book by ID |
| PUT | `/books/{id}` | Update a book |
| DELETE | `/books/{id}` | Delete a book |
| GET | `/health` | Health check |

## Required Fields

- `title` (string, required)
- `author` (string, required)
- `year` (integer, required)
- `isbn` (string, optional)

## Prerequisites

- Java 21
- Maven 3.9+

## Build

```bash
mvn clean package
```

## Run

```bash
mvn spring-boot:run
```

The API will be available at `http://localhost:8080`.

## Test

```bash
mvn test
```

## Example Usage

Create a book:

```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937,"isbn":"978-0547928227"}'
```

List books:

```bash
curl http://localhost:8080/books
```

Filter by author:

```bash
curl "http://localhost:8080/books?author=Tolkien"
```

Health check:

```bash
curl http://localhost:8080/health
```
