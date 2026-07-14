# Book Collection REST API

A RESTful API service for managing a book collection, built with Java and Spring Boot. Data is stored in an embedded H2 database.

## Requirements
- Java 17 or higher
- Maven 3.6+

## Setup and Run Instructions

1. Clone or download this project.
2. Navigate to the project root directory.
3. Build and run the application using Maven:
   ```bash
   mvn spring-boot:run
   ```
   The server will start on `http://localhost:8080`.

## API Endpoints

### Health Check
- `GET /health`
- Returns the health status of the API.
- **Response**: `{"status": "UP"}` (200 OK)

### Books
- `POST /books`
  - **Description**: Create a new book.
  - **Request Body**: 
    ```json
    {
      "title": "1984",
      "author": "George Orwell",
      "year": 1949,
      "isbn": "1234567890"
    }
    ```
    *(Note: `title` and `author` are required)*
  - **Response**: Created book object (201 Created)

- `GET /books`
  - **Description**: List all books. Supports filtering by author.
  - **Query Parameters**: `?author=George Orwell` (optional, case-insensitive)
  - **Response**: Array of book objects (200 OK)

- `GET /books/{id}`
  - **Description**: Get a single book by its ID.
  - **Response**: Book object (200 OK) or `404 Not Found`

- `PUT /books/{id}`
  - **Description**: Update an existing book.
  - **Request Body**: Same as POST.
  - **Response**: Updated book object (200 OK) or `404 Not Found`

- `DELETE /books/{id}`
  - **Description**: Delete a book by its ID.
  - **Response**: `204 No Content` or `404 Not Found`

## Testing

Run the integration tests using Maven:
```bash
mvn test
```

The test suite includes:
1. Creating and retrieving a book.
2. Validating required fields (title and author).
3. Filtering books by author.
4. Verifying the health check endpoint.