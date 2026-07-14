# Book Collection REST API

A REST API service for managing a book collection built with FastAPI and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Input validation for all fields
- SQLite database for data storage
- JSON responses with appropriate HTTP status codes
- Health check endpoint

## Requirements

- Python 3.8+
- See `requirements.txt` for dependencies

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <project-directory>
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the API

Start the server:
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.

## API Documentation

Once the server is running, you can access:
- Interactive API documentation: `http://localhost:8000/docs`
- Alternative documentation: `http://localhost:8000/redoc`

## Endpoints

### Health Check
- `GET /health` - Check if the API is running

### Books

#### Create a book
- `POST /books` - Create a new book
  - Request body:
    ```json
    {
      "title": "Book Title",
      "author": "Author Name",
      "year": 2023,
      "isbn": "978-3-16-148410-0"
    }
    ```
  - Required fields: `title`, `author`
  - Returns: `201 Created` with the created book

#### List all books
- `GET /books` - Get all books
  - Query parameter: `author` (optional) - filter by author name
  - Returns: `200 OK` with list of books

#### Get a single book
- `GET /books/{id}` - Get a book by ID
  - Returns: `200 OK` with book details or `404 Not Found`

#### Update a book
- `PUT /books/{id}` - Update a book
  - Request body: Partial update with any fields to change
  - Returns: `200 OK` with updated book or `404 Not Found`

#### Delete a book
- `DELETE /books/{id}` - Delete a book
  - Returns: `204 No Content` or `404 Not Found`

## Data Validation

- `title`: Required, minimum 1 character
- `author`: Required, minimum 1 character
- `year`: Optional, between 1000 and 9999
- `isbn`: Optional, must contain only digits and hyphens

## Database

The API uses SQLite with a single `books` table. The database file (`books.db`) is created automatically in the project directory.

## Testing

Run tests with:
```bash
pytest
```

## Example Usage

```bash
# Create a book
curl -X POST "http://localhost:8000/books" \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925}'

# List all books
curl "http://localhost:8000/books"

# Filter by author
curl "http://localhost:8000/books?author=Fitzgerald"

# Get a specific book
curl "http://localhost:8000/books/1"

# Update a book
curl -X PUT "http://localhost:8000/books/1" \
  -H "Content-Type: application/json" \
  -d '{"year": 1926}'

# Delete a book
curl -X DELETE "http://localhost:8000/books/1"
```