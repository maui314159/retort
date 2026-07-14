package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"strconv"
	"testing"
)

func setupTestApp(t *testing.T) (*App, func()) {
	tmpfile, err := os.CreateTemp("", "test_*.db")
	if err != nil {
		t.Fatalf("Failed to create temp db: %v", err)
	}
	tmpfile.Close()

	store, err := NewBookStore(tmpfile.Name())
	if err != nil {
		t.Fatalf("Failed to create store: %v", err)
	}

	cleanup := func() {
		store.Close()
		os.Remove(tmpfile.Name())
	}

	return NewApp(store), cleanup
}

func TestHealthCheck(t *testing.T) {
	app, cleanup := setupTestApp(t)
	defer cleanup()

	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	w := httptest.NewRecorder()
	app.healthHandler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
	}

	var response map[string]string
	if err := json.NewDecoder(w.Body).Decode(&response); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if response["status"] != "ok" {
		t.Errorf("Expected status 'ok', got '%s'", response["status"])
	}
}

func TestCreateAndListBooks(t *testing.T) {
	app, cleanup := setupTestApp(t)
	defer cleanup()

	// Create a book
	bookData := map[string]interface{}{
		"title":  "The Go Programming Language",
		"author": "Alan A. A. Donovan",
		"year":   2015,
		"isbn":   "978-0134190440",
	}
	body, _ := json.Marshal(bookData)
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
	w := httptest.NewRecorder()
	app.createBookHandler(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("Expected status %d, got %d", http.StatusCreated, w.Code)
	}

	// List books
	req = httptest.NewRequest(http.MethodGet, "/books", nil)
	w = httptest.NewRecorder()
	app.listBooksHandler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
	}

	var books []Book
	if err := json.NewDecoder(w.Body).Decode(&books); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if len(books) != 1 {
		t.Errorf("Expected 1 book, got %d", len(books))
	}
	if books[0].Title != "The Go Programming Language" {
		t.Errorf("Expected title 'The Go Programming Language', got '%s'", books[0].Title)
	}
}

func TestCreateBookValidation(t *testing.T) {
	app, cleanup := setupTestApp(t)
	defer cleanup()

	// Missing title and author
	bookData := map[string]interface{}{
		"year": 2015,
	}
	body, _ := json.Marshal(bookData)
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
	w := httptest.NewRecorder()
	app.createBookHandler(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status %d, got %d", http.StatusBadRequest, w.Code)
	}
}

func TestGetUpdateDeleteBook(t *testing.T) {
	app, cleanup := setupTestApp(t)
	defer cleanup()

	book, err := app.store.CreateBook("1984", "George Orwell", 1949, "978-0451524935")
	if err != nil {
		t.Fatalf("Failed to create book: %v", err)
	}

	idStr := strconv.Itoa(book.ID)

	// Get book
	req := httptest.NewRequest(http.MethodGet, "/books/"+idStr, nil)
	w := httptest.NewRecorder()
	app.getBookHandler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
	}

	// Update book
	updateData := map[string]interface{}{
		"title":  "Nineteen Eighty-Four",
		"author": "George Orwell",
		"year":   1949,
		"isbn":   "978-0451524935",
	}
	body, _ := json.Marshal(updateData)
	req = httptest.NewRequest(http.MethodPut, "/books/"+idStr, bytes.NewReader(body))
	w = httptest.NewRecorder()
	app.updateBookHandler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
	}

	// Delete book
	req = httptest.NewRequest(http.MethodDelete, "/books/"+idStr, nil)
	w = httptest.NewRecorder()
	app.deleteBookHandler(w, req)

	if w.Code != http.StatusNoContent {
		t.Errorf("Expected status %d, got %d", http.StatusNoContent, w.Code)
	}

	// Verify deletion
	req = httptest.NewRequest(http.MethodGet, "/books/"+idStr, nil)
	w = httptest.NewRecorder()
	app.getBookHandler(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status %d, got %d", http.StatusNotFound, w.Code)
	}
}
