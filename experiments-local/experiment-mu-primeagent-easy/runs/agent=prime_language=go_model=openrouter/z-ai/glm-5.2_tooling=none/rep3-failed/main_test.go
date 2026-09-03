package main

import (
	"bytes"
	"context"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

// newTestServer builds a fresh SQLite-backed server for each test.
func newTestServer(t *testing.T) (*httptest.Server, *Store) {
	t.Helper()
	dbPath := t.TempDir() + "/test.db"
	store, err := NewStore(dbPath)
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	t.Cleanup(func() { _ = store.Close() })

	h := &handlers{store: store}
	srv := httptest.NewServer(h.routes())
	t.Cleanup(srv.Close)
	return srv, store
}

func do(t *testing.T, srv *httptest.Server, method, path string, body interface{}) *httptest.ResponseRecorder {
	t.Helper()
	var r *http.Request
	if body != nil {
		buf, _ := json.Marshal(body)
		r = httptest.NewRequest(method, path, bytes.NewReader(buf))
		r.Header.Set("Content-Type", "application/json")
	} else {
		r = httptest.NewRequest(method, path, nil)
	}
	rr := httptest.NewRecorder()
	srv.Config.Handler.ServeHTTP(rr, r)
	return rr
}

// TestCreateAndGetBook covers POST creation and GET-by-id retrieval,
// including proper status codes and JSON shape.
func TestCreateAndGetBook(t *testing.T) {
	srv, store := newTestServer(t)
	_ = store

	rr := do(t, srv, "POST", "/books", map[string]interface{}{
		"title":  "A Game of Thrones",
		"author": "George R. R. Martin",
		"year":   1996,
		"isbn":   "9780553103540",
	})
	if rr.Code != http.StatusCreated {
		t.Fatalf("expected 201 Created, got %d: %s", rr.Code, rr.Body.String())
	}
	var created Book
	if err := json.Unmarshal(rr.Body.Bytes(), &created); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if created.ID == 0 || created.Title != "A Game of Thrones" || created.Author != "George R. R. Martin" {
		t.Fatalf("unexpected book: %+v", created)
	}
	if created.Year == nil || *created.Year != 1996 {
		t.Fatalf("unexpected year: %v", created.Year)
	}

	// GET by id.
	rr = do(t, srv, "GET", "/books/1", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", rr.Code, rr.Body.String())
	}
	var got Book
	if err := json.Unmarshal(rr.Body.Bytes(), &got); err != nil {
		t.Fatalf("unmarshal get: %v", err)
	}
	if got.ID != created.ID || got.Title != created.Title || got.Author != created.Author || got.ISBN != created.ISBN {
		t.Fatalf("expected %+v, got %+v", created, got)
	}
	if got.Year == nil || *got.Year != *created.Year {
		t.Fatalf("year mismatch: expected %v, got %v", created.Year, got.Year)
	}
}

// TestListFilterAndValidation exercises listing, the author filter, and
// input validation (title/author required).
func TestListFilterAndValidation(t *testing.T) {
	srv, _ := newTestServer(t)

	// Validation: missing title and author.
	rr := do(t, srv, "POST", "/books", map[string]interface{}{
		"year": 2001,
	})
	if rr.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 for missing required fields, got %d: %s", rr.Code, rr.Body.String())
	}
	var errBody map[string]string
	_ = json.Unmarshal(rr.Body.Bytes(), &errBody)
	if errBody["error"] == "" {
		t.Fatalf("expected error message, got %s", rr.Body.String())
	}

	// Create a couple of books with different authors.
	for _, b := range []map[string]interface{}{
		{"title": "Book A", "author": "Alice"},
		{"title": "Book B", "author": "Bob"},
		{"title": "Book C", "author": "alice"}, // different case
	} {
		rr := do(t, srv, "POST", "/books", b)
		if rr.Code != http.StatusCreated {
			t.Fatalf("create failed: %d %s", rr.Code, rr.Body.String())
		}
	}

	// List all.
	rr = do(t, srv, "GET", "/books", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("list: expected 200, got %d", rr.Code)
	}
	var all []Book
	if err := json.Unmarshal(rr.Body.Bytes(), &all); err != nil {
		t.Fatalf("unmarshal list: %v", err)
	}
	if len(all) != 3 {
		t.Fatalf("expected 3 books, got %d", len(all))
	}

	// Filter by author (case-insensitive exact match). "Alice" and "alice"
	// should both match the query ?author=alice.
	rr = do(t, srv, "GET", "/books?author=alice", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("filter: expected 200, got %d", rr.Code)
	}
	var filtered []Book
	if err := json.Unmarshal(rr.Body.Bytes(), &filtered); err != nil {
		t.Fatalf("unmarshal filtered: %v", err)
	}
	if len(filtered) != 2 {
		t.Fatalf("expected 2 books for author=alice, got %d", len(filtered))
	}
	for _, b := range filtered {
		if b.Author != "Alice" && b.Author != "alice" {
			t.Fatalf("unexpected author in filter: %q", b.Author)
		}
	}
}

// TestUpdateDeleteAndNotFound covers update, delete, and the not-found
// status codes for unknown ids.
func TestUpdateDeleteAndNotFound(t *testing.T) {
	srv, _ := newTestServer(t)

	// Seed a book.
	rr := do(t, srv, "POST", "/books", map[string]interface{}{
		"title":  "Original Title",
		"author": "Original Author",
		"year":   2010,
	})
	if rr.Code != http.StatusCreated {
		t.Fatalf("seed: %d %s", rr.Code, rr.Body.String())
	}
	var seed Book
	_ = json.Unmarshal(rr.Body.Bytes(), &seed)

	// Update only the title.
	newTitle := "Updated Title"
	rr = do(t, srv, "PUT", "/books/1", map[string]interface{}{
		"title": newTitle,
	})
	if rr.Code != http.StatusOK {
		t.Fatalf("update: expected 200, got %d: %s", rr.Code, rr.Body.String())
	}
	var updated Book
	_ = json.Unmarshal(rr.Body.Bytes(), &updated)
	if updated.Title != newTitle || updated.Author != "Original Author" {
		t.Fatalf("partial update wrong: %+v", updated)
	}
	if updated.Year == nil || *updated.Year != 2010 {
		t.Fatalf("update dropped year: %v", updated.Year)
	}

	// Update with empty title should fail validation.
	rr = do(t, srv, "PUT", "/books/1", map[string]interface{}{
		"title": "   ",
	})
	if rr.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 for blank title on update, got %d: %s", rr.Code, rr.Body.String())
	}

	// Not found cases.
	rr = do(t, srv, "GET", "/books/999", nil)
	if rr.Code != http.StatusNotFound {
		t.Fatalf("expected 404 for missing book, got %d", rr.Code)
	}
	rr = do(t, srv, "PUT", "/books/999", map[string]interface{}{"title": "X"})
	if rr.Code != http.StatusNotFound {
		t.Fatalf("expected 404 for updating missing book, got %d", rr.Code)
	}

	// Delete.
	rr = do(t, srv, "DELETE", "/books/1", nil)
	if rr.Code != http.StatusNoContent {
		t.Fatalf("delete: expected 204, got %d: %s", rr.Code, rr.Body.String())
	}
	rr = do(t, srv, "GET", "/books/1", nil)
	if rr.Code != http.StatusNotFound {
		t.Fatalf("get after delete: expected 404, got %d", rr.Code)
	}

	// Deleting again is idempotent (still 204).
	rr = do(t, srv, "DELETE", "/books/1", nil)
	if rr.Code != http.StatusNoContent {
		t.Fatalf("idempotent delete: expected 204, got %d", rr.Code)
	}
}

// TestHealthCheck verifies the health endpoint returns 200.
func TestHealthCheck(t *testing.T) {
	srv, _ := newTestServer(t)
	rr := do(t, srv, "GET", "/health", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("health: expected 200, got %d", rr.Code)
	}
	var body map[string]string
	if err := json.Unmarshal(rr.Body.Bytes(), &body); err != nil {
		t.Fatalf("health unmarshal: %v", err)
	}
	if body["status"] != "ok" {
		t.Fatalf("health status: %q", body["status"])
	}
}

// TestStoreDirectly verifies the Store layer independently of HTTP.
func TestStoreDirectly(t *testing.T) {
	store, err := NewStore(t.TempDir() + "/direct.db")
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	defer store.Close()

	// Ping the underlying DB to make sure it is usable.
	if err := store.db.PingContext(context.Background()); err != nil {
		t.Fatalf("ping: %v", err)
	}

	y := 1949
	b, err := store.Create("Nineteen Eighty-Four", "George Orwell", &y, "")
	if err != nil {
		t.Fatalf("create: %v", err)
	}
	if b.ID != 1 || b.Year == nil || *b.Year != 1949 {
		t.Fatalf("unexpected book: %+v", b)
	}

	// author filter via List.
	all, err := store.List("")
	if err != nil || len(all) != 1 {
		t.Fatalf("List: %v len=%d", err, len(all))
	}

	// Get unknown id.
	if _, err := store.Get(999); err != ErrNotFound {
		t.Fatalf("expected ErrNotFound, got %v", err)
	}

	// Ensure the implicit interface assertion holds (sql.DB usage).
	var _ *sql.DB = store.db
}
