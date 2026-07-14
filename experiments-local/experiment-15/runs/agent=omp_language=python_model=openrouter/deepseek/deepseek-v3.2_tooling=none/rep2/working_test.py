#!/usr/bin/env python3
"""
Working test that sets DATABASE_URL before importing.
"""
import os
import sys

# Set environment variable BEFORE importing main
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from main import app, BookDB, Base, engine, get_db
from fastapi.testclient import TestClient
from sqlalchemy import create_engine as create_engine_sql
from sqlalchemy.orm import sessionmaker

print(f"Using database URL: {os.environ['DATABASE_URL']}")
print(f"Engine URL: {engine.url}")

# Verify tables are created on the in-memory engine
print("Creating tables...")
Base.metadata.create_all(bind=engine)
print("Tables created")

# Create test client
client = TestClient(app)

def run_tests():
    print("\nRunning tests...")
    print("=" * 50)
    
    # Test health endpoint
    print("Test 1: Health check")
    response = client.get("/health")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.json()}")
    assert response.status_code == 200
    print("  ✓ Health check passed")
    
    # Test creating a book
    print("\nTest 2: Create book")
    book_data = {
        "title": "Test Book",
        "author": "Test Author",
        "year": 2023,
        "isbn": "1234567890"
    }
    response = client.post("/books", json=book_data)
    print(f"  Status: {response.status_code}")
    if response.status_code == 201:
        book = response.json()
        print(f"  Created book ID: {book['id']}")
        print(f"  Title: {book['title']}")
        print("  ✓ Create book passed")
        return book['id']
    else:
        print(f"  Response: {response.text}")
        print("  ✗ Create book failed")
        return None

def main():
    try:
        book_id = run_tests()
        if book_id:
            print("\n✅ Basic tests passed!")
            return 0
        else:
            print("\n❌ Tests failed")
            return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())