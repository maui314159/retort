package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strconv"
	"testing"
)

// newTestAPI returns an API backed by an isolated in-memory SQLite DB.
func newTestAPI(t *testing.T) (*API, func()) {
	t.Helper()
	dir := t.TempDir()
	store, err := NewStore(filepath.Join(dir, "test.db"))
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	api := NewAPI(store)
	cleanup := func() {
		if err := store.Close(); err != nil {
			t.Logf("close store: %v", err)
		}
	}
	return api, cleanup
}

func doRequest(t *testing.T, h http.Handler, method, target string, body interface{}) *httptest.ResponseRecorder {
	t.Helper()
	var buf bytes.Buffer
	if body != nil {
		b, err := json.Marshal(body)
		if err != nil {
			t.Fatalf("marshal body: %v", err)
		}
		buf.Write(b)
	}
	req := httptest.NewRequest(method, target, &buf)
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

// TestCreateGetBook verifies a book can be created and then retrieved by ID.
func TestCreateGetBook(t *testing.T) {
	api, cleanup := newTestAPI(t)
	defer cleanup()
	h := api.Handler()

	payload := map[string]interface{}{
		"title":  "The Go Programming Language",
		"author": "Donovan & Kernighan",
		"year":   2015,
		"isbn":   "978-0134190440",
	}
	rec := doRequest(t, h, http.MethodPost, "/books", payload)
	if rec.Code != http.StatusCreated {
		t.Fatalf("expected 201, got %d: %s", rec.Code, rec.Body.String())
	}
	var created Book
	if err := json.Unmarshal(rec.Body.Bytes(), &created); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if created.ID == 0 || created.Title != "The Go Programming Language" {
		t.Fatalf("unexpected book: %+v", created)
	}

	rec = doRequest(t, h, http.MethodGet, "/books/"+strconv.FormatInt(created.ID, 10), nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", rec.Code, rec.Body.String())
	}
	var got Book
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if got.Title != created.Title || got.ID != created.ID {
		t.Fatalf("mismatch: got %+v want %+v", got, created)
	}
}

// TestValidation checks that missing required fields return 400.
func TestValidation(t *testing.T) {
	api, cleanup := newTestAPI(t)
	defer cleanup()
	h := api.Handler()

	// Missing author entirely.
	rec := doRequest(t, h, http.MethodPost, "/books", map[string]interface{}{
		"title": "No Author Book",
	})
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 for missing author, got %d: %s", rec.Code, rec.Body.String())
	}

	// Empty title.
	rec = doRequest(t, h, http.MethodPost, "/books", map[string]interface{}{
		"title":  "",
		"author": "Someone",
	})
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 for empty title, got %d: %s", rec.Code, rec.Body.String())
	}

	// Invalid JSON body.
	rec = doRequest(t, h, http.MethodPost, "/books", nil)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 for empty body, got %d: %s", rec.Code, rec.Body.String())
	}
}

// TestListFilterDelete verifies listing, author filtering, and deletion.
func TestListFilterDelete(t *testing.T) {
	api, cleanup := newTestAPI(t)
	defer cleanup()
	h := api.Handler()

	books := []map[string]interface{}{
		{"title": "Book A", "author": "Alice", "year": 2001, "isbn": "a"},
		{"title": "Book B", "author": "Bob", "year": 2002, "isbn": "b"},
		{"title": "Book C", "author": "Alice", "year": 2003, "isbn": "c"},
	}
	for _, b := range books {
		rec := doRequest(t, h, http.MethodPost, "/books", b)
		if rec.Code != http.StatusCreated {
			t.Fatalf("create failed: %d %s", rec.Code, rec.Body.String())
		}
	}

	// List all.
	rec := doRequest(t, h, http.MethodGet, "/books", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("list: %d %s", rec.Code, rec.Body.String())
	}
	var all []Book
	if err := json.Unmarshal(rec.Body.Bytes(), &all); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if len(all) != 3 {
		t.Fatalf("expected 3 books, got %d", len(all))
	}

	// Filter by author=Alice.
	rec = doRequest(t, h, http.MethodGet, "/books?author=Alice", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("filter: %d %s", rec.Code, rec.Body.String())
	}
	var filtered []Book
	if err := json.Unmarshal(rec.Body.Bytes(), &filtered); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if len(filtered) != 2 {
		t.Fatalf("expected 2 Alice books, got %d", len(filtered))
	}
	for _, b := range filtered {
		if b.Author != "Alice" {
			t.Fatalf("unexpected author: %s", b.Author)
		}
	}

	// Update one book via PUT.
	rec = doRequest(t, h, http.MethodPut, "/books/1", map[string]interface{}{
		"title": "Book A Updated", "author": "Alice", "year": 2010, "isbn": "a2",
	})
	if rec.Code != http.StatusOK {
		t.Fatalf("update: %d %s", rec.Code, rec.Body.String())
	}

	// Delete book 1.
	rec = doRequest(t, h, http.MethodDelete, "/books/1", nil)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("delete: %d %s", rec.Code, rec.Body.String())
	}
	// Deleting again should 404.
	rec = doRequest(t, h, http.MethodDelete, "/books/1", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("second delete expected 404, got %d", rec.Code)
	}
}

// TestHealth verifies the health endpoint.
func TestHealth(t *testing.T) {
	api, cleanup := newTestAPI(t)
	defer cleanup()
	h := api.Handler()

	rec := doRequest(t, h, http.MethodGet, "/health", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", rec.Code, rec.Body.String())
	}
	var resp map[string]string
	if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if resp["status"] != "ok" {
		t.Fatalf("unexpected status: %q", resp["status"])
	}
}
