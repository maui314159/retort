package main

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"testing"
)

// newTestServer returns a Server backed by a fresh in-memory SQLite DB.
func newTestServer(t *testing.T) *Server {
	t.Helper()
	dir := t.TempDir()
	store, err := NewSQLiteStore(filepath.Join(dir, "test.db"))
	if err != nil {
		t.Fatalf("init store: %v", err)
	}
	t.Cleanup(func() { _ = store.Close() })
	return NewServer(store)
}

func do(t *testing.T, s *Server, method, target string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var r *http.Request
	if body == nil {
		r = httptest.NewRequest(method, target, nil)
	} else {
		buf, err := json.Marshal(body)
		if err != nil {
			t.Fatalf("marshal body: %v", err)
		}
		r = httptest.NewRequest(method, target, bytes.NewReader(buf))
		r.Header.Set("Content-Type", "application/json")
	}
	w := httptest.NewRecorder()
	s.ServeHTTP(w, r)
	return w
}

func TestCreateGetBook(t *testing.T) {
	s := newTestServer(t)

	// Create
	w := do(t, s, "POST", "/books", Book{Title: "The Go Prog. Lang.", Author: "Donovan", Year: 2015, ISBN: "978013"})
	if w.Code != http.StatusCreated {
		t.Fatalf("create status = %d, want %d; body=%s", w.Code, http.StatusCreated, w.Body.String())
	}
	var created Book
	if err := json.Unmarshal(w.Body.Bytes(), &created); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if created.ID == 0 {
		t.Fatal("expected non-zero id")
	}
	if created.Title != "The Go Prog. Lang." {
		t.Fatalf("title = %q", created.Title)
	}

	// Get by id
	w = do(t, s, "GET", "/books/1", nil)
	if w.Code != http.StatusOK {
		t.Fatalf("get status = %d, body=%s", w.Code, w.Body.String())
	}
	var got Book
	if err := json.Unmarshal(w.Body.Bytes(), &got); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if got.ID != created.ID || got.Title != created.Title {
		t.Fatalf("got = %+v, want %+v", got, created)
	}

	// NotFound for unknown id
	w = do(t, s, "GET", "/books/9999", nil)
	if w.Code != http.StatusNotFound {
		t.Fatalf("notfound status = %d, want %d", w.Code, http.StatusNotFound)
	}
}

func TestValidationRejectsEmptyFields(t *testing.T) {
	s := newTestServer(t)

	// Missing title
	w := do(t, s, "POST", "/books", Book{Author: "X"})
	if w.Code != http.StatusBadRequest {
		t.Fatalf("missing-title status = %d, want %d", w.Code, http.StatusBadRequest)
	}

	// Missing author
	w = do(t, s, "POST", "/books", Book{Title: "X"})
	if w.Code != http.StatusBadRequest {
		t.Fatalf("missing-author status = %d, want %d", w.Code, http.StatusBadRequest)
	}

	// Empty body
	w = do(t, s, "POST", "/books", nil)
	if w.Code != http.StatusBadRequest {
		t.Fatalf("empty-body status = %d, want %d", w.Code, http.StatusBadRequest)
	}
}

func TestListFilterUpdateDelete(t *testing.T) {
	s := newTestServer(t)
	ctx := context.Background()

	// Seed two books by one author, one by another.
	seed := []Book{
		{Title: "A1", Author: "Alice", Year: 2001, ISBN: "i1"},
		{Title: "A2", Author: "Alice", Year: 2002, ISBN: "i2"},
		{Title: "B1", Author: "Bob", Year: 2010, ISBN: "i3"},
	}
	for i := range seed {
		id, err := s.store.Create(ctx, &seed[i])
		if err != nil {
			t.Fatalf("seed create: %v", err)
		}
		seed[i].ID = id
	}

	// List all
	w := do(t, s, "GET", "/books", nil)
	if w.Code != http.StatusOK {
		t.Fatalf("list status = %d", w.Code)
	}
	var all []Book
	if err := json.Unmarshal(w.Body.Bytes(), &all); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if len(all) != 3 {
		t.Fatalf("len(all) = %d, want 3", len(all))
	}

	// Filter by author
	w = do(t, s, "GET", "/books?author=Alice", nil)
	if w.Code != http.StatusOK {
		t.Fatalf("list filter status = %d", w.Code)
	}
	var filtered []Book
	if err := json.Unmarshal(w.Body.Bytes(), &filtered); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if len(filtered) != 2 {
		t.Fatalf("len(filtered) = %d, want 2", len(filtered))
	}
	for _, b := range filtered {
		if b.Author != "Alice" {
			t.Fatalf("unexpected author %q", b.Author)
		}
	}

	// Update
	w = do(t, s, "PUT", "/books/1", Book{Title: "A1-updated", Author: "Alice", Year: 2099, ISBN: "i1"})
	if w.Code != http.StatusOK {
		t.Fatalf("update status = %d, body=%s", w.Code, w.Body.String())
	}
	w = do(t, s, "GET", "/books/1", nil)
	var got Book
	if err := json.Unmarshal(w.Body.Bytes(), &got); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if got.Title != "A1-updated" || got.Year != 2099 {
		t.Fatalf("update not applied: %+v", got)
	}

	// Update nonexistent -> 404
	w = do(t, s, "PUT", "/books/9999", Book{Title: "X", Author: "Y"})
	if w.Code != http.StatusNotFound {
		t.Fatalf("update-missing status = %d, want 404", w.Code)
	}

	// Delete
	w = do(t, s, "DELETE", "/books/2", nil)
	if w.Code != http.StatusNoContent {
		t.Fatalf("delete status = %d, want %d", w.Code, http.StatusNoContent)
	}
	// Delete again -> 404
	w = do(t, s, "DELETE", "/books/2", nil)
	if w.Code != http.StatusNotFound {
		t.Fatalf("delete-missing status = %d, want 404", w.Code)
	}

	// Confirm count
	w = do(t, s, "GET", "/books", nil)
	var after []Book
	_ = json.Unmarshal(w.Body.Bytes(), &after)
	if len(after) != 2 {
		t.Fatalf("after delete len = %d, want 2", len(after))
	}
}

func TestHealth(t *testing.T) {
	s := newTestServer(t)
	w := do(t, s, "GET", "/health", nil)
	if w.Code != http.StatusOK {
		t.Fatalf("health status = %d", w.Code)
	}
	var m map[string]string
	if err := json.Unmarshal(w.Body.Bytes(), &m); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if m["status"] != "ok" {
		t.Fatalf("status = %q", m["status"])
	}
}
