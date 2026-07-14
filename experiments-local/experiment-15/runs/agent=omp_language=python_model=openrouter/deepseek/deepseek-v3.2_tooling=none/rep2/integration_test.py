#!/usr/bin/env python3
"""
Integration test for the Book Collection API.
Starts the server, runs tests, then shuts down.
"""
import sys
import subprocess
import time
import requests
import json
import atexit

def start_server():
    """Start the FastAPI server in a subprocess."""
    import os
    cmd = [sys.executable, "main.py"]
    # Set environment to use in-memory database
    env = os.environ.copy()
    env['DATABASE_URL'] = 'sqlite:///:memory:'
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2)  # Give server time to start
    return proc

def stop_server(proc):
    """Stop the server subprocess."""
    proc.terminate()
    proc.wait()

def test_endpoint(url, method="GET", data=None, expected_status=200):
    """Test an API endpoint."""
    try:
        if method == "GET":
            resp = requests.get(url, timeout=5)
        elif method == "POST":
            resp = requests.post(url, json=data, timeout=5)
        elif method == "PUT":
            resp = requests.put(url, json=data, timeout=5)
        elif method == "DELETE":
            resp = requests.delete(url, timeout=5)
        else:
            raise ValueError(f"Unknown method: {method}")
        
        if resp.status_code != expected_status:
            print(f"  FAIL: Expected status {expected_status}, got {resp.status_code}")
            print(f"        Response: {resp.text[:200]}")
            return False, resp
        
        print(f"  OK: {method} {url} -> {resp.status_code}")
        return True, resp
    except Exception as e:
        print(f"  ERROR: {method} {url} -> {e}")
        return False, None

def main():
    print("Starting Book Collection API integration test...")
    
    # Start server
    print("\n1. Starting server...")
    server = start_server()
    atexit.register(lambda: stop_server(server))
    
    base_url = "http://localhost:8000"
    
    # Test health endpoint
    print("\n2. Testing health endpoint...")
    ok, resp = test_endpoint(f"{base_url}/health", "GET", expected_status=200)
    if not ok:
        print("Health check failed, stopping.")
        return 1
    
    # Test creating a book
    print("\n3. Testing book creation...")
    book_data = {
        "title": "The Hitchhiker's Guide to the Galaxy",
        "author": "Douglas Adams",
        "year": 1979,
        "isbn": "9780345391803"
    }
    ok, resp = test_endpoint(f"{base_url}/books", "POST", book_data, expected_status=201)
    if not ok:
        return 1
    
    created_book = resp.json()
    book_id = created_book['id']
    print(f"  Created book ID: {book_id}")
    
    # Test listing books
    print("\n4. Testing book listing...")
    ok, resp = test_endpoint(f"{base_url}/books", "GET", expected_status=200)
    if not ok:
        return 1
    
    books = resp.json()
    print(f"  Found {len(books)} book(s)")
    if len(books) != 1:
        print(f"  FAIL: Expected 1 book, got {len(books)}")
        return 1
    
    # Test getting specific book
    print(f"\n5. Testing get book by ID ({book_id})...")
    ok, resp = test_endpoint(f"{base_url}/books/{book_id}", "GET", expected_status=200)
    if not ok:
        return 1
    
    book = resp.json()
    if book['title'] != book_data['title']:
        print(f"  FAIL: Title mismatch: {book['title']} != {book_data['title']}")
        return 1
    
    # Test updating book
    print(f"\n6. Testing book update ({book_id})...")
    update_data = {"title": "The Restaurant at the End of the Universe", "year": 1980}
    ok, resp = test_endpoint(f"{base_url}/books/{book_id}", "PUT", update_data, expected_status=200)
    if not ok:
        return 1
    
    updated = resp.json()
    if updated['title'] != update_data['title']:
        print(f"  FAIL: Title not updated: {updated['title']} != {update_data['title']}")
        return 1
    
    # Test listing with author filter
    print("\n7. Testing author filter...")
    ok, resp = test_endpoint(f"{base_url}/books?author=Douglas", "GET", expected_status=200)
    if not ok:
        return 1
    
    filtered = resp.json()
    if len(filtered) != 1:
        print(f"  FAIL: Expected 1 book with author 'Douglas', got {len(filtered)}")
        return 1
    
    # Test deleting book
    print(f"\n8. Testing book deletion ({book_id})...")
    ok, resp = test_endpoint(f"{base_url}/books/{book_id}", "DELETE", expected_status=204)
    if not ok:
        return 1
    
    # Verify book is deleted
    print(f"\n9. Verifying book is deleted...")
    ok, resp = test_endpoint(f"{base_url}/books/{book_id}", "GET", expected_status=404)
    if not ok:
        return 1
    
    # Test validation
    print("\n10. Testing validation...")
    bad_data = {"title": "Missing Author"}
    ok, resp = test_endpoint(f"{base_url}/books", "POST", bad_data, expected_status=422)
    if not ok:
        return 1
    
    print("\n✅ All tests passed!")
    return 0

if __name__ == "__main__":
    # First, modify main.py to use in-memory database for testing
    with open("main.py", "r") as f:
        content = f.read()
    
    # Replace DATABASE_URL with in-memory for testing
    if 'DATABASE_URL = "sqlite:///./books.db"' in content:
        content = content.replace(
            'DATABASE_URL = "sqlite:///./books.db"',
            'DATABASE_URL = "sqlite:///:memory:"'
        )
        with open("main.py", "w") as f:
            f.write(content)
        print("Modified main.py to use in-memory database for testing")
    
    try:
        sys.exit(main())
    finally:
        # Restore original DATABASE_URL
        with open("main.py", "r") as f:
            content = f.read()
        if 'DATABASE_URL = "sqlite:///:memory:"' in content:
            content = content.replace(
                'DATABASE_URL = "sqlite:///:memory:"',
                'DATABASE_URL = "sqlite:///./books.db"'
            )
            with open("main.py", "w") as f:
                f.write(content)
            print("\nRestored main.py to use file-based database")