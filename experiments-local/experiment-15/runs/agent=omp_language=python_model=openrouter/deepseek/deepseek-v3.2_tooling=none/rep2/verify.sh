#!/bin/bash
echo "=== Book Collection API Verification ==="
echo

echo "1. Checking required files..."
for file in main.py requirements.txt README.md; do
    if [ -f "$file" ]; then
        echo "   ✓ $file exists"
    else
        echo "   ✗ $file missing"
        exit 1
    fi
done
echo

echo "2. Checking Python dependencies..."
python -c "import fastapi, sqlalchemy, pydantic, uvicorn" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "   ✓ All dependencies installed"
else
    echo "   ✗ Missing dependencies"
    exit 1
fi
echo

echo "3. Testing the API..."
echo "   Starting server in background..."
DATABASE_URL="sqlite:///:memory:" python main.py > /dev/null 2>&1 &
SERVER_PID=$!
sleep 2

echo "   Testing endpoints..."
echo "   - Health check:"
curl -s http://localhost:8000/health | grep -q '"status":"healthy"'
if [ $? -eq 0 ]; then
    echo "     ✓ Healthy"
else
    echo "     ✗ Failed"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

echo "   - Creating a book:"
BOOK_RESPONSE=$(curl -s -X POST http://localhost:8000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"Test Book","author":"Test Author","year":2023,"isbn":"1234567890"}')
echo $BOOK_RESPONSE | grep -q '"id"'
if [ $? -eq 0 ]; then
    echo "     ✓ Book created"
    BOOK_ID=$(echo $BOOK_RESPONSE | python -c "import sys, json; print(json.load(sys.stdin)['id'])")
else
    echo "     ✗ Failed to create book"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

echo "   - Listing books:"
LIST_RESPONSE=$(curl -s http://localhost:8000/books)
echo $LIST_RESPONSE | grep -q '"title":"Test Book"'
if [ $? -eq 0 ]; then
    echo "     ✓ Books listed"
else
    echo "     ✗ Failed to list books"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

echo "   - Getting specific book:"
GET_RESPONSE=$(curl -s http://localhost:8000/books/$BOOK_ID)
echo $GET_RESPONSE | grep -q '"title":"Test Book"'
if [ $? -eq 0 ]; then
    echo "     ✓ Book retrieved"
else
    echo "     ✗ Failed to get book"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

echo "   - Deleting book:"
DELETE_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE http://localhost:8000/books/$BOOK_ID)
if [ "$DELETE_STATUS" = "204" ]; then
    echo "     ✓ Book deleted"
else
    echo "     ✗ Failed to delete book (status: $DELETE_STATUS)"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

echo "   - Verifying deletion:"
GET_AFTER_DELETE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/books/$BOOK_ID)
if [ "$GET_AFTER_DELETE" = "404" ]; then
    echo "     ✓ Book not found (as expected)"
else
    echo "     ✗ Book still exists (status: $GET_AFTER_DELETE)"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

kill $SERVER_PID 2>/dev/null
echo
echo "=== All tests passed! ==="
echo
echo "To run the application:"
echo "  python main.py"
echo "Or:"
echo "  uvicorn main:app --reload --host 0.0.0.0 --port 8000"
echo
echo "API documentation will be available at:"
echo "  http://localhost:8000/docs"
echo "  http://localhost:8000/redoc"