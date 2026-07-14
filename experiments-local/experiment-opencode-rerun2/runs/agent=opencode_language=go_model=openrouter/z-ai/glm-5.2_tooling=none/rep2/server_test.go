package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

// newTestServer returns a Server backed by an in-memory SQLite DB.
func newTestServer(t *testing.T) *Server {
	t.Helper()
	store, err := NewStore(":memory:")
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewServer(store)
}

func doRequest(t *testing.T, srv http.Handler, method, path string, body interface{}) *httptest.ResponseRecorder {
	t.Helper()
	var buf bytes.Buffer
	if body != nil {
		if err := json.NewEncoder(&buf).Encode(body); err != nil {
			t.Fatalf("encode body: %v", err)
		}
	}
	req := httptest.NewRequest(method, path, &buf)
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	srv.ServeHTTP(rec, req)
	return rec
}

func TestCreateListGetBook(t *testing.T) {
	srv := newTestServer(t)

	// Create
	rec := doRequest(t, srv, http.MethodPost, "/books", map[string]interface{}{
		"title":  "The Go Programming Language",
		"author": "Donovan",
		"year":   2015,
		"isbn":   "978-0134190440",
	})
	if rec.Code != http.StatusCreated {
		t.Fatalf("create: expected 201, got %d: %s", rec.Code, rec.Body.String())
	}
	var created Book
	if err := json.Unmarshal(rec.Body.Bytes(), &created); err != nil {
		t.Fatalf("unmarshal created: %v", err)
	}
	if created.ID == 0 || created.Title != "The Go Programming Language" {
		t.Fatalf("unexpected created book: %+v", created)
	}

	// List
	rec = doRequest(t, srv, http.MethodGet, "/books", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("list: expected 200, got %d", rec.Code)
	}
	var list []Book
	if err := json.Unmarshal(rec.Body.Bytes(), &list); err != nil {
		t.Fatalf("unmarshal list: %v", err)
	}
	if len(list) != 1 {
		t.Fatalf("expected 1 book, got %d", len(list))
	}

	// Get by ID
	rec = doRequest(t, srv, http.MethodGet, "/books/1", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("get: expected 200, got %d", rec.Code)
	}
	var got Book
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("unmarshal get: %v", err)
	}
	if got.ID != 1 {
		t.Fatalf("expected id 1, got %d", got.ID)
	}
}

func TestValidationRejectsMissingFields(t *testing.T) {
	srv := newTestServer(t)

	// Missing author.
	rec := doRequest(t, srv, http.MethodPost, "/books", map[string]interface{}{
		"title": "No Author",
	})
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 for missing author, got %d: %s", rec.Code, rec.Body.String())
	}

	// Missing title.
	rec = doRequest(t, srv, http.MethodPost, "/books", map[string]interface{}{
		"author": "Someone",
	})
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 for missing title, got %d: %s", rec.Code, rec.Body.String())
	}

	// Empty body.
	rec = doRequest(t, srv, http.MethodPost, "/books", nil)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 for empty body, got %d: %s", rec.Code, rec.Body.String())
	}
}

func TestUpdateAndDeleteBook(t *testing.T) {
	srv := newTestServer(t)

	// Seed a book.
	rec := doRequest(t, srv, http.MethodPost, "/books", map[string]interface{}{
		"title":  "Old Title",
		"author": "Old Author",
		"year":   2000,
	})
	if rec.Code != http.StatusCreated {
		t.Fatalf("create: expected 201, got %d: %s", rec.Code, rec.Body.String())
	}

	// Update.
	rec = doRequest(t, srv, http.MethodPut, "/books/1", map[string]interface{}{
		"title": "New Title",
	})
	if rec.Code != http.StatusOK {
		t.Fatalf("update: expected 200, got %d: %s", rec.Code, rec.Body.String())
	}
	var updated Book
	if err := json.Unmarshal(rec.Body.Bytes(), &updated); err != nil {
		t.Fatalf("unmarshal update: %v", err)
	}
	if updated.Title != "New Title" || updated.Author != "Old Author" {
		t.Fatalf("unexpected updated book: %+v", updated)
	}

	// Update nonexistent -> 404.
	rec = doRequest(t, srv, http.MethodPut, "/books/999", map[string]interface{}{
		"title": "X",
	})
	if rec.Code != http.StatusNotFound {
		t.Fatalf("expected 404 updating missing book, got %d", rec.Code)
	}

	// Delete.
	rec = doRequest(t, srv, http.MethodDelete, "/books/1", nil)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("delete: expected 204, got %d", rec.Code)
	}

	// Get deleted -> 404.
	rec = doRequest(t, srv, http.MethodGet, "/books/1", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("expected 404 for deleted book, got %d", rec.Code)
	}

	// Delete again -> 404.
	rec = doRequest(t, srv, http.MethodDelete, "/books/1", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("expected 404 deleting missing book, got %d", rec.Code)
	}
}

func TestAuthorFilterAndHealth(t *testing.T) {
	srv := newTestServer(t)

	for _, b := range []map[string]interface{}{
		{"title": "A", "author": "Alice"},
		{"title": "B", "author": "Bob"},
		{"title": "C", "author": "Alice Smith"},
	} {
		rec := doRequest(t, srv, http.MethodPost, "/books", b)
		if rec.Code != http.StatusCreated {
			t.Fatalf("create: expected 201, got %d: %s", rec.Code, rec.Body.String())
		}
	}

	// Filter by author=Alice (substring, case-insensitive).
	rec := doRequest(t, srv, http.MethodGet, "/books?author=Alice", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("list filter: expected 200, got %d", rec.Code)
	}
	var list []Book
	if err := json.Unmarshal(rec.Body.Bytes(), &list); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if len(list) != 2 {
		t.Fatalf("expected 2 alice books, got %d", len(list))
	}

	// Health.
	rec = doRequest(t, srv, http.MethodGet, "/health", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("health: expected 200, got %d", rec.Code)
	}
	var h map[string]string
	if err := json.Unmarshal(rec.Body.Bytes(), &h); err != nil {
		t.Fatalf("unmarshal health: %v", err)
	}
	if h["status"] != "ok" {
		t.Fatalf("expected status ok, got %q", h["status"])
	}
}
