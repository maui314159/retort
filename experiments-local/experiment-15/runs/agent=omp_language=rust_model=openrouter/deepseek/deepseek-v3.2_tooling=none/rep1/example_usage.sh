#!/bin/bash

echo "Starting the book API server in the background..."
cargo run &
SERVER_PID=$!

# Wait for server to start
sleep 2

echo "Testing health endpoint:"
curl -s -X GET http://localhost:3000/health

echo -e "\n\nCreating a book:"
curl -s -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Rust Programming Language",
    "author": "Steve Klabnik",
    "year": 2018,
    "isbn": "978-1593278281"
  }' | jq .

echo -e "\nCreating another book:"
curl -s -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Clean Code",
    "author": "Robert C. Martin",
    "year": 2008,
    "isbn": "978-0132350884"
  }' | jq .

echo -e "\nListing all books:"
curl -s -X GET http://localhost:3000/books | jq .

echo -e "\nListing books by author 'Steve Klabnik':"
curl -s -X GET "http://localhost:3000/books?author=Steve%20Klabnik" | jq .

echo -e "\nTrying to create duplicate ISBN (should fail):"
curl -s -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Another Rust Book",
    "author": "Different Author",
    "year": 2020,
    "isbn": "978-1593278281"
  }' | jq .

# Get the ID of the first book
echo -e "\nGetting first book ID..."
BOOK_ID=$(curl -s -X GET http://localhost:3000/books | jq -r '.[0].id')
echo "Book ID: $BOOK_ID"

echo -e "\nGetting book by ID:"
curl -s -X GET http://localhost:3000/books/$BOOK_ID | jq .

echo -e "\nUpdating the book:"
curl -s -X PUT http://localhost:3000/books/$BOOK_ID \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Rust Programming Language (2nd Edition)",
    "year": 2023
  }' | jq .

echo -e "\nDeleting the book:"
curl -s -X DELETE http://localhost:3000/books/$BOOK_ID

echo -e "\nTrying to get deleted book (should fail):"
curl -s -X GET http://localhost:3000/books/$BOOK_ID | jq .

echo -e "\nStopping the server..."
kill $SERVER_PID