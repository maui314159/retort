package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
)

func setupTestAPI(t *testing.T) (*API, func()) {
	t.Helper()
	f, err := os.CreateTemp("", "books_test_*.db")
	if err != nil {
		t.Fatalf("create temp db: %v", err)
	}
	path := f.Name()
	f.Close()

	store, err := NewBookStore(path)
	if err != nil {
		os.Remove(path)
		t.Fatalf("open store: %v", err)
	}
	cleanup := func() {
		store.Close()
		os.Remove(path)
	}
	return NewAPI(store), cleanup
}

func TestHealthCheck(t *testing.T) {
	api, cleanup := setupTestAPI(t)
	defer cleanup()

	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	rr := httptest.NewRecorder()
	api.ServeHTTP(rr, req)

	if rr.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rr.Code)
	}
	var body map[string]string
	if err := json.NewDecoder(rr.Body).Decode(&body); err != nil {
		t.Fatalf("decode response: %v", err)
	}
	if body["status"] != "ok" {
		t.Fatalf("expected status ok, got %q", body["status"])
	}
}

func TestCreateAndGetBook(t *testing.T) {
	api, cleanup := setupTestAPI(t)
	defer cleanup()

	// Create
	book := Book{Title: "The Go Programming Language", Author: "Donovan & Kernighan", Year: 2015, ISBN: "978-0134190440"}
	body, _ := json.Marshal(book)
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()
	api.ServeHTTP(rr, req)

	if rr.Code != http.StatusCreated {
		t.Fatalf("create: expected 201, got %d; body: %s", rr.Code, rr.Body.String())
	}
	var created Book
	if err := json.NewDecoder(rr.Body).Decode(&created); err != nil {
		t.Fatalf("decode created: %v", err)
	}
	if created.ID == 0 {
		t.Fatal("expected non-zero ID")
	}
	if created.Title != book.Title {
		t.Fatalf("expected title %q, got %q", book.Title, created.Title)
	}

	// Get by ID
	req = httptest.NewRequest(http.MethodGet, "/books/1", nil)
	rr = httptest.NewRecorder()
	api.ServeHTTP(rr, req)

	if rr.Code != http.StatusOK {
		t.Fatalf("get: expected 200, got %d", rr.Code)
	}
	var fetched Book
	if err := json.NewDecoder(rr.Body).Decode(&fetched); err != nil {
		t.Fatalf("decode fetched: %v", err)
	}
	if fetched.Title != book.Title {
		t.Fatalf("expected title %q, got %q", book.Title, fetched.Title)
	}
	if fetched.Year != 2015 {
		t.Fatalf("expected year 2015, got %d", fetched.Year)
	}
}

func TestListBooksWithAuthorFilter(t *testing.T) {
	api, cleanup := setupTestAPI(t)
	defer cleanup()

	// Create two books by different authors
	books := []Book{
		{Title: "Book A", Author: "Alice", Year: 2020},
		{Title: "Book B", Author: "Bob", Year: 2021},
		{Title: "Book C", Author: "Alice", Year: 2022},
	}
	for _, b := range books {
		body, _ := json.Marshal(b)
		req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
		req.Header.Set("Content-Type", "application/json")
		rr := httptest.NewRecorder()
		api.ServeHTTP(rr, req)
		if rr.Code != http.StatusCreated {
			t.Fatalf("create book: expected 201, got %d", rr.Code)
		}
	}

	// List all
	req := httptest.NewRequest(http.MethodGet, "/books", nil)
	rr := httptest.NewRecorder()
	api.ServeHTTP(rr, req)
	if rr.Code != http.StatusOK {
		t.Fatalf("list all: expected 200, got %d", rr.Code)
	}
	var all []Book
	json.NewDecoder(rr.Body).Decode(&all)
	if len(all) != 3 {
		t.Fatalf("expected 3 books, got %d", len(all))
	}

	// Filter by author
	req = httptest.NewRequest(http.MethodGet, "/books?author=Alice", nil)
	rr = httptest.NewRecorder()
	api.ServeHTTP(rr, req)
	if rr.Code != http.StatusOK {
		t.Fatalf("list filtered: expected 200, got %d", rr.Code)
	}
	var filtered []Book
	json.NewDecoder(rr.Body).Decode(&filtered)
	if len(filtered) != 2 {
		t.Fatalf("expected 2 books by Alice, got %d", len(filtered))
	}
	for _, b := range filtered {
		if b.Author != "Alice" {
			t.Fatalf("expected author Alice, got %q", b.Author)
		}
	}
}

func TestUpdateBook(t *testing.T) {
	api, cleanup := setupTestAPI(t)
	defer cleanup()

	// Create
	book := Book{Title: "Original", Author: "Author", Year: 2000}
	body, _ := json.Marshal(book)
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
	rr := httptest.NewRecorder()
	api.ServeHTTP(rr, req)
	var created Book
	json.NewDecoder(rr.Body).Decode(&created)

	// Update
	updated := Book{Title: "Updated", Author: "New Author", Year: 2024, ISBN: "978-1234"}
	body, _ = json.Marshal(updated)
	req = httptest.NewRequest(http.MethodPut, "/books/1", bytes.NewReader(body))
	rr = httptest.NewRecorder()
	api.ServeHTTP(rr, req)

	if rr.Code != http.StatusOK {
		t.Fatalf("update: expected 200, got %d; body: %s", rr.Code, rr.Body.String())
	}
	var result Book
	json.NewDecoder(rr.Body).Decode(&result)
	if result.Title != "Updated" {
		t.Fatalf("expected title Updated, got %q", result.Title)
	}
	if result.ISBN != "978-1234" {
		t.Fatalf("expected isbn 978-1234, got %q", result.ISBN)
	}
}

func TestDeleteBook(t *testing.T) {
	api, cleanup := setupTestAPI(t)
	defer cleanup()

	// Create
	book := Book{Title: "To Delete", Author: "Author"}
	body, _ := json.Marshal(book)
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
	rr := httptest.NewRecorder()
	api.ServeHTTP(rr, req)

	// Delete
	req = httptest.NewRequest(http.MethodDelete, "/books/1", nil)
	rr = httptest.NewRecorder()
	api.ServeHTTP(rr, req)
	if rr.Code != http.StatusNoContent {
		t.Fatalf("delete: expected 204, got %d", rr.Code)
	}

	// Verify gone
	req = httptest.NewRequest(http.MethodGet, "/books/1", nil)
	rr = httptest.NewRecorder()
	api.ServeHTTP(rr, req)
	if rr.Code != http.StatusNotFound {
		t.Fatalf("get deleted: expected 404, got %d", rr.Code)
	}

	// Delete again — 404
	req = httptest.NewRequest(http.MethodDelete, "/books/1", nil)
	rr = httptest.NewRecorder()
	api.ServeHTTP(rr, req)
	if rr.Code != http.StatusNotFound {
		t.Fatalf("delete missing: expected 404, got %d", rr.Code)
	}
}

func TestCreateBookValidation(t *testing.T) {
	api, cleanup := setupTestAPI(t)
	defer cleanup()

	// Missing title
	body, _ := json.Marshal(Book{Author: "Author"})
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()
	api.ServeHTTP(rr, req)
	if rr.Code != http.StatusBadRequest {
		t.Fatalf("missing title: expected 400, got %d", rr.Code)
	}

	// Missing author
	body, _ = json.Marshal(Book{Title: "Title"})
	req = httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	rr = httptest.NewRecorder()
	api.ServeHTTP(rr, req)
	if rr.Code != http.StatusBadRequest {
		t.Fatalf("missing author: expected 400, got %d", rr.Code)
	}
}

func TestGetBookNotFound(t *testing.T) {
	api, cleanup := setupTestAPI(t)
	defer cleanup()

	req := httptest.NewRequest(http.MethodGet, "/books/999", nil)
	rr := httptest.NewRecorder()
	api.ServeHTTP(rr, req)
	if rr.Code != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", rr.Code)
	}
}
