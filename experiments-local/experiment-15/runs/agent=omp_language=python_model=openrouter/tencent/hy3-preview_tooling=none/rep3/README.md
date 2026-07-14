# Book Collection REST API

A simple REST API service for managing a book collection, built with Python, FastAPI, and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Input validation for required fields
- SQLite database for data persistence
- Health check endpoint

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/books` | Create a new book |
| GET | `/books` | List all books (supports `?author=` filter) |
| GET | `/books/{id}` | Get a single book by ID |
| PUT | `/books/{id}` | Update a book |
| DELETE | `/books/{id}` | Delete a book |

## Book Object

```json
{
  "id": 1,
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "9780743273565"
}
```

### Fields

- `title` (required): Book title
- `author` (required): Book author
- `year` (optional): Publication year (0-2100)
- `isbn` (optional): ISBN (10 or 13 digits, must be unique)

## Setup

### Prerequisites

- Python 3.8+ installed

### Installation

1. Clone or download this directory
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the Application

### Development mode (with auto-reload)

```bash
uvicorn main:app --reload
```

### Production mode

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Direct execution

```bash
python main.py
```

The API will be available at `http://localhost:8000`

### Interactive API Documentation

FastAPI provides automatic interactive documentation:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Running Tests

```bash
pytest test_api.py -v
```

For test coverage:

```bash
pytest test_api.py --cov=main --cov-report=term-missing
```

## Example Usage

### Create a book

```bash
curl -X POST "http://localhost:8000/books" \
  -H "Content-Type: application/json" \
  -d '{"title": "1984", "author": "George Orwell", "year": 1949}'
```

### List all books

```bash
curl "http://localhost:8000/books"
```

### Filter by author

```bash
curl "http://localhost:8000/books?author=orwell"
```

### Get a specific book

```bash
curl "http://localhost:8000/books/1"
```

### Update a book

```bash
curl -X PUT "http://localhost:8000/books/1" \
  -H "Content-Type: application/json" \
  -d '{"year": 1950}'
```

### Delete a book

```bash
curl -X DELETE "http://localhost:8000/books/1"
```

## Project Structure

```
.
├── main.py           # FastAPI application with all endpoints
├── test_api.py       # Test suite
├── requirements.txt  # Python dependencies
├── README.md         # This file
└── books.db         # SQLite database (created on first run)
```
