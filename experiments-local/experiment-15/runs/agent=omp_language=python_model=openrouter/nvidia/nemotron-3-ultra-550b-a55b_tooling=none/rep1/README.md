# Book Collection API

A REST API service for managing a book collection built with FastAPI and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Input validation with Pydantic
- Health check endpoint
- SQLite database storage

## Requirements

- Python 3.10+
- pip

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

Start the development server:
```bash
uvicorn main:app --reload
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive docs (Swagger UI)**: http://localhost:8000/docs
- **Alternative docs (ReDoc)**: http://localhost:8000/redoc
- **Health check**: http://localhost:8000/health

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Health check |
| POST | /books | Create a new book |
| GET | /books | List all books (supports ?author= filter) |
| GET | /books/{id} | Get a single book by ID |
| PUT | /books/{id} | Update a book |
| DELETE | /books/{id} | Delete a book |

## Book Schema

```json
{
  "title": "string (required, 1-255 chars)",
  "author": "string (required, 1-255 chars)",
  "year": "integer (optional, 1000-2100)",
  "isbn": "string (optional, ISBN-10 or ISBN-13 format)"
}
```

## Example Usage

### Create a book
```bash
curl -X POST http://localhost:8000/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "9780743273565"
  }'
```

### List all books
```bash
curl http://localhost:8000/books
```

### List books by author
```bash
curl "http://localhost:8000/books?author=Fitzgerald"
```

### Get a single book
```bash
curl http://localhost:8000/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:8000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"year": 1926}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:8000/books/1
```

## Running Tests

```bash
pytest test_main.py -v
```

Or with coverage:
```bash
pytest test_main.py -v --cov=main --cov=database --cov=models
```

## Project Structure

```
.
├── main.py          # FastAPI application
├── database.py      # Database connection and schema
├── models.py        # Pydantic models for validation
├── test_main.py     # Unit and integration tests
├── requirements.txt # Python dependencies
└── README.md        # This file
```

## License

MIT
