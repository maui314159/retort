package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

// newTestHandler returns a Handler backed by an in-memory SQLite store.
func newTestHandler(t *testing.T) *Handler {
	t.Helper()
	store, err := NewStore(":memory:")
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	t.Cleanup(func() { _ = store.Close() })
	return NewHandler(store)
}

// do performs an authenticated-style request against the handler under test.
func do(t *testing.T, h http.Handler, method, target string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var r *bytes.Reader
	if body != nil {
		b, err := json.Marshal(body)
		if err != nil {
			t.Fatalf("marshal body: %v", err)
		}
		r = bytes.NewReader(b)
	} else {
		r = bytes.NewReader(nil)
	}
	req := httptest.NewRequest(method, target, r)
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func TestHealth(t *testing.T) {
	h := newTestHandler(t).Routes()
	rec := do(t, h, "GET", "/health", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", rec.Code, rec.Body.String())
	}
	var got map[string]string
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if got["status"] != "ok" {
		t.Fatalf("expected status ok, got %q", got["status"])
	}
}

func TestCreateListGetUpdateDelete(t *testing.T) {
	h := newTestHandler(t).Routes()

	// Create
	rec := do(t, h, "POST", "/books", map[string]any{
		"title": "The Go Programming Language", "author": "Donovan & Kernighan", "year": 2015, "isbn": "978-0134190440",
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
	rec = do(t, h, "GET", "/books", nil)
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

	// List with author filter returns the matching book.
	rec = do(t, h, "GET", "/books?author=Donovan+%26+Kernighan", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("list filter: expected 200, got %d", rec.Code)
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &list); err != nil {
		t.Fatalf("unmarshal filtered list: %v", err)
	}
	if len(list) != 1 || list[0].ID != created.ID {
		t.Fatalf("filter mismatch: %+v", list)
	}

	// List with a non-matching author filter returns empty.
	rec = do(t, h, "GET", "/books?author=nobody", nil)
	if err := json.Unmarshal(rec.Body.Bytes(), &list); err != nil {
		t.Fatalf("unmarshal empty list: %v", err)
	}
	if len(list) != 0 {
		t.Fatalf("expected 0 books for nobody, got %d", len(list))
	}

	// Get by id
	rec = do(t, h, "GET", "/books/1", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("get: expected 200, got %d", rec.Code)
	}
	var got Book
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("unmarshal get: %v", err)
	}
	if got.ID != created.ID || got.Author != "Donovan & Kernighan" {
		t.Fatalf("get mismatch: %+v", got)
	}

	// Update
	rec = do(t, h, "PUT", "/books/1", map[string]any{
		"title": "Updated Title", "author": "New Author", "year": 2020, "isbn": "x",
	})
	if rec.Code != http.StatusOK {
		t.Fatalf("update: expected 200, got %d: %s", rec.Code, rec.Body.String())
	}
	var updated Book
	if err := json.Unmarshal(rec.Body.Bytes(), &updated); err != nil {
		t.Fatalf("unmarshal updated: %v", err)
	}
	if updated.Title != "Updated Title" || updated.Author != "New Author" {
		t.Fatalf("update mismatch: %+v", updated)
	}

	// Delete
	rec = do(t, h, "DELETE", "/books/1", nil)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("delete: expected 204, got %d", rec.Code)
	}

	// Get after delete -> 404
	rec = do(t, h, "GET", "/books/1", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("get after delete: expected 404, got %d", rec.Code)
	}
}

func TestValidation(t *testing.T) {
	h := newTestHandler(t).Routes()

	cases := []struct {
		name string
		body map[string]any
	}{
		{"missing author", map[string]any{"title": "T"}},
		{"missing title", map[string]any{"author": "A"}},
		{"empty title and author", map[string]any{"title": "", "author": ""}},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			rec := do(t, h, "POST", "/books", c.body)
			if rec.Code != http.StatusBadRequest {
				t.Fatalf("expected 400, got %d: %s", rec.Code, rec.Body.String())
			}
			var resp map[string]string
			if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
				t.Fatalf("unmarshal: %v", err)
			}
			if resp["error"] == "" {
				t.Fatal("expected non-empty error message")
			}
		})
	}

	// Invalid JSON
	req := httptest.NewRequest("POST", "/books", bytes.NewBufferString("{bad json"))
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("invalid json: expected 400, got %d", rec.Code)
	}

	// Unknown field rejected
	rec = do(t, h, "POST", "/books", map[string]any{"title": "T", "author": "A", "bogus": 1})
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("unknown field: expected 400, got %d: %s", rec.Code, rec.Body.String())
	}
}

func TestNotFoundAndBadID(t *testing.T) {
	h := newTestHandler(t).Routes()

	// Non-existent id
	rec := do(t, h, "GET", "/books/999", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", rec.Code)
	}

	// Non-numeric id -> 400 (no matching route in Go 1.22 mux returns 404)
	rec = do(t, h, "GET", "/books/abc", nil)
	if rec.Code != http.StatusNotFound && rec.Code != http.StatusBadRequest {
		t.Fatalf("expected 404 or 400, got %d", rec.Code)
	}
}
