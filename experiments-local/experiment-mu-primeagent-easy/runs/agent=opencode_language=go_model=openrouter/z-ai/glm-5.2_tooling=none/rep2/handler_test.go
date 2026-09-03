package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

// newTestServer returns a Handler backed by an in-memory SQLite DB.
func newTestServer(t *testing.T) (*Handler, func()) {
	t.Helper()
	store, err := NewStore(":memory:")
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	cleanup := func() { _ = store.Close() }
	return NewHandler(store), cleanup
}

// do sends a request to the handler and returns the response recorder.
func do(t *testing.T, h *Handler, method, target string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var buf bytes.Buffer
	if body != nil {
		if err := json.NewEncoder(&buf).Encode(body); err != nil {
			t.Fatalf("encode body: %v", err)
		}
	}
	req := httptest.NewRequest(method, target, &buf)
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	mux := http.NewServeMux()
	h.Routes(mux)
	mux.ServeHTTP(rec, req)
	return rec
}

func TestCreateGetListDelete(t *testing.T) {
	h, cleanup := newTestServer(t)
	defer cleanup()

	// Health check
	rec := do(t, h, http.MethodGet, "/health", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("health status = %d, want %d", rec.Code, http.StatusOK)
	}

	// Create
	book := map[string]any{"title": "Dune", "author": "Herbert", "year": 1965, "isbn": "ABC"}
	rec = do(t, h, http.MethodPost, "/books", book)
	if rec.Code != http.StatusCreated {
		t.Fatalf("create status = %d, body = %s", rec.Code, rec.Body.String())
	}
	var created Book
	if err := json.Unmarshal(rec.Body.Bytes(), &created); err != nil {
		t.Fatalf("unmarshal created: %v", err)
	}
	if created.ID == 0 {
		t.Fatal("expected non-zero id")
	}

	// Get
	rec = do(t, h, http.MethodGet, "/books/1", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("get status = %d", rec.Code)
	}
	var got Book
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("unmarshal get: %v", err)
	}
	if got.Title != "Dune" {
		t.Fatalf("title = %q", got.Title)
	}

	// List
	rec = do(t, h, http.MethodGet, "/books", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("list status = %d", rec.Code)
	}
	var list []Book
	if err := json.Unmarshal(rec.Body.Bytes(), &list); err != nil {
		t.Fatalf("unmarshal list: %v", err)
	}
	if len(list) != 1 {
		t.Fatalf("list len = %d, want 1", len(list))
	}

	// List with author filter
	rec = do(t, h, http.MethodGet, "/books?author=Herbert", nil)
	if err := json.Unmarshal(rec.Body.Bytes(), &list); err != nil {
		t.Fatalf("unmarshal list filtered: %v", err)
	}
	if len(list) != 1 {
		t.Fatalf("filtered len = %d, want 1", len(list))
	}
	rec = do(t, h, http.MethodGet, "/books?author=Nobody", nil)
	if err := json.Unmarshal(rec.Body.Bytes(), &list); err != nil {
		t.Fatalf("unmarshal list filtered empty: %v", err)
	}
	if len(list) != 0 {
		t.Fatalf("filtered empty len = %d, want 0", len(list))
	}

	// Delete
	rec = do(t, h, http.MethodDelete, "/books/1", nil)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("delete status = %d", rec.Code)
	}
	// Delete again -> 404
	rec = do(t, h, http.MethodDelete, "/books/1", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("delete missing status = %d, want 404", rec.Code)
	}
}

func TestValidation(t *testing.T) {
	h, cleanup := newTestServer(t)
	defer cleanup()

	cases := []struct {
		name string
		body map[string]any
	}{
		{"missing title", map[string]any{"author": "A", "year": 2000}},
		{"missing author", map[string]any{"title": "T", "year": 2000}},
		{"empty title", map[string]any{"title": "", "author": "A"}},
	}
	for _, c := range cases {
		rec := do(t, h, http.MethodPost, "/books", c.body)
		if rec.Code != http.StatusBadRequest {
			t.Fatalf("%s: status = %d, want 400, body = %s", c.name, rec.Code, rec.Body.String())
		}
	}

	// PUT with invalid body on existing book should also 400
	book := map[string]any{"title": "T", "author": "A"}
	rec := do(t, h, http.MethodPost, "/books", book)
	if rec.Code != http.StatusCreated {
		t.Fatalf("create status = %d", rec.Code)
	}
	rec = do(t, h, http.MethodPut, "/books/1", map[string]any{"title": "", "author": "A"})
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("put validation status = %d, want 400", rec.Code)
	}
}

func TestUpdateAndGetNotFound(t *testing.T) {
	h, cleanup := newTestServer(t)
	defer cleanup()

	// Get nonexistent
	rec := do(t, h, http.MethodGet, "/books/999", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("get missing status = %d, want 404", rec.Code)
	}

	// Create + update
	rec = do(t, h, http.MethodPost, "/books", map[string]any{"title": "Old", "author": "A", "year": 2000})
	if rec.Code != http.StatusCreated {
		t.Fatalf("create status = %d", rec.Code)
	}
	var created Book
	_ = json.Unmarshal(rec.Body.Bytes(), &created)

	rec = do(t, h, http.MethodPut, "/books/1", map[string]any{"title": "New", "author": "B", "year": 2010, "isbn": "XYZ"})
	if rec.Code != http.StatusOK {
		t.Fatalf("update status = %d, body = %s", rec.Code, rec.Body.String())
	}
	var updated Book
	if err := json.Unmarshal(rec.Body.Bytes(), &updated); err != nil {
		t.Fatalf("unmarshal updated: %v", err)
	}
	if updated.Title != "New" || updated.Author != "B" || updated.Year != 2010 || updated.ISBN != "XYZ" {
		t.Fatalf("updated book = %+v", updated)
	}

	// Update nonexistent -> 404
	rec = do(t, h, http.MethodPut, "/books/999", map[string]any{"title": "X", "author": "Y"})
	if rec.Code != http.StatusNotFound {
		t.Fatalf("update missing status = %d, want 404", rec.Code)
	}

	// Invalid id
	rec = do(t, h, http.MethodGet, "/books/abc", nil)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("invalid id status = %d, want 400", rec.Code)
	}
}
