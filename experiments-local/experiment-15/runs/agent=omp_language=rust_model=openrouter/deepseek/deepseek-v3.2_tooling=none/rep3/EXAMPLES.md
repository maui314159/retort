# API Usage Examples

## Start the server
```bash
cargo run
# Server starts on http://localhost:3000
```

## Health Check
```bash
curl -X GET http://localhost:3000/health
```

## Create a Book
```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Rust Programming Language",
    "author": "Steve Klabnik and Carol Nichols",
    "year": 2018,
    "isbn": "978-1593278281"
  }'
```

## List All Books
```bash
curl -X GET http://localhost:3000/books
```

## Filter Books by Author
```bash
curl -X GET "http://localhost:3000/books?author=Steve%20Klabnik%20and%20Carol%20Nichols"
```

## Get a Specific Book
```bash
# Replace {id} with the actual book ID from the create response
curl -X GET http://localhost:3000/books/{id}
```

## Update a Book
```bash
curl -X PUT http://localhost:3000/books/{id} \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated Title",
    "author": "Updated Author"
  }'
```

## Delete a Book
```bash
curl -X DELETE http://localhost:3000/books/{id}
```

## Validation Examples

### Missing Required Field (title)
```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{
    "author": "Test Author"
  }'
```

### Missing Required Field (author)
```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Book"
  }'
```

### Invalid Year
```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Book",
    "author": "Test Author",
    "year": -1
  }'
```