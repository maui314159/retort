# books-api

A small REST API for managing a book collection, built with Java 17+ and
Javalin 6, backed by SQLite. No external services required.

## Requirements

- Java 17 or newer (tested on Java 25)
- Maven 3.8+

## Endpoints

| Method | Path             | Body                  | Status          | Description                          |
|--------|------------------|-----------------------|-----------------|--------------------------------------|
| GET    | `/health`        | —                     | 200             | Liveness check                       |
| GET    | `/books`         | —                     | 200             | List books (`?author=` to filter)    |
| GET    | `/books/{id}`    | —                     | 200 / 404       | Fetch one book                       |
| POST   | `/books`         | `{title,author,year?,isbn?}` | 201 / 400   | Create a book                        |
| PUT    | `/books/{id}`    | `{title,author,year?,isbn?}` | 200 / 400 / 404 | Update a book                    |
| DELETE | `/books/{id}`    | —                     | 204 / 404       | Delete a book                        |

`title` and `author` are required. `year` and `isbn` are optional. Validation
errors return `400` with a `details` array:

```json
{"error":"validation failed","details":["title is required"]}
```

## Build

```sh
mvn package
```

This produces:
- `target/books-api.jar` — the application jar
- `target/lib/` — runtime dependencies

## Run

```sh
# default: port 7000, db file ./books.db
java -jar target/books-api.jar

# custom port and db path
java -jar target/books-api.jar 8080 /var/data/books.db

# in-memory db (lost on exit)
java -jar target/books-api.jar 7000 :memory:

# alternative: use the dependency lib directory directly
java -cp "target/books-api.jar:target/lib/*" com.example.books.App
```

A shutdown hook closes the database cleanly on Ctrl-C / SIGTERM.

## Examples

```sh
# health
curl http://localhost:7000/health
# -> {"status":"ok"}

# create
curl -X POST http://localhost:7000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"0441172717"}'
# -> {"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"0441172717"}

# list with author filter
curl 'http://localhost:7000/books?author=Frank%20Herbert'

# fetch one
curl http://localhost:7000/books/1

# update
curl -X PUT http://localhost:7000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Dune (2nd ed.)","author":"Frank Herbert","year":1965}'

# delete
curl -X DELETE http://localhost:7000/books/1
```

## Tests

```sh
mvn test
```

21 tests cover:
- **`BookRepositoryTest`** — direct CRUD against the in-memory SQLite store.
- **`BookApiTest`** — full HTTP lifecycle (POST/GET/PUT/DELETE), `?author=`
  filtering, sequential id assignment, via Javalin's embedded server.
- **`BookApiValidationTest`** — missing required fields, blank values,
  unknown ids (404), non-numeric ids (400), malformed JSON (400).

## Project layout

```
src/
├── main/java/com/example/books/
│   ├── App.java              # entry point + argument parsing
│   ├── Book.java             # entity
│   ├── BookRepository.java   # SQLite store
│   └── BookController.java   # routes + validation
└── test/java/com/example/books/
    ├── BookRepositoryTest.java
    ├── BookApiTest.java
    └── BookApiValidationTest.java
```

## Design notes

- **Storage:** one `books` table (`id`, `title`, `author`, `year`, `isbn`).
  Writes are serialized on a single connection since SQLite is
  single-writer; reads scale across Javalin's thread pool.
- **Validation:** `BookController.BookInput#validate()` is the single
  source of truth for "required" semantics; the controller returns all
  errors at once rather than failing on the first one.
- **Error format:** simple `{"error": "...", "details": [...]}` shape. The
  global exception handler converts anything unexpected to a 500 without
  leaking the stack trace to the client.
- **Why Javalin:** smallest reasonable embeddable HTTP layer in the JVM
  ecosystem; no Spring context, no annotations, one `pom.xml` to read.
