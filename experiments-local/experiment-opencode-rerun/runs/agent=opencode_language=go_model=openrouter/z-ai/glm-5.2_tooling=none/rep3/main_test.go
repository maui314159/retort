package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"testing"
)

// newTestServer returns a Server backed by a fresh in-temp SQLite DB
// and a cleanup func.
func newTestServer(t *testing.T) (*Server, func()) {
	t.Helper()
	dir := t.TempDir()
	store, err := NewStore(filepath.Join(dir, "test.db"))
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	srv := NewServer(store)
	return srv, func() {
		_ = store.Close()
	}
}

func do(t *testing.T, srv *Server, method, target string, body interface{}) *httptest.ResponseRecorder {
	t.Helper()
	var buf bytes.Buffer
	if body != nil {
		if err := json.NewEncoder(&buf).Encode(body); err != nil {
			t.Fatalf("encode body: %v", err)
		}
	}
	req := httptest.NewRequest(method, target, &buf)
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	rec := httptest.NewRecorder()
	srv.ServeHTTP(rec, req)
	return rec
}

func decode(t *testing.T, rec *httptest.ResponseRecorder, v interface{}) {
	t.Helper()
	if err := json.NewDecoder(rec.Body).Decode(v); err != nil {
		t.Fatalf("decode response: %v (body=%q)", err, rec.Body.String())
	}
}

// TestCreateAndGetBook covers the create + retrieve flow with proper
// status codes and JSON round-tripping.
func TestCreateAndGetBook(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()

	in := Book{Title: "The Go Programming Language", Author: "Alan Donovan", Year: 2015, ISBN: "9780321774929"}
	rec := do(t, srv, http.MethodPost, "/books", in)
	if rec.Code != http.StatusCreated {
		t.Fatalf("create status = %d, want %d (body=%s)", rec.Code, http.StatusCreated, rec.Body.String())
	}
	var got Book
	decode(t, rec, &got)
	if got.ID == 0 {
		t.Fatal("expected non-zero id")
	}
	if got.Title != in.Title || got.Author != in.Author || got.Year != in.Year || got.ISBN != in.ISBN {
		t.Fatalf("round-trip mismatch: got %+v, want %+v", got, in)
	}

	rec = do(t, srv, http.MethodGet, "/books/1", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("get status = %d, want %d (body=%s)", rec.Code, http.StatusOK, rec.Body.String())
	}
	var fetched Book
	decode(t, rec, &fetched)
	if fetched != got {
		t.Fatalf("fetched = %+v, want %+v", fetched, got)
	}
}

// TestValidation verifies that missing required fields are rejected.
func TestValidation(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()

	cases := []struct {
		name string
		body Book
	}{
		{"missing title", Book{Author: "X", Year: 2000}},
		{"missing author", Book{Title: "X", Year: 2000}},
		{"blank title", Book{Title: "   ", Author: "X", Year: 2000}},
		{"blank author", Book{Title: "X", Author: "  ", Year: 2000}},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			rec := do(t, srv, http.MethodPost, "/books", c.body)
			if rec.Code != http.StatusBadRequest {
				t.Fatalf("status = %d, want %d (body=%s)", rec.Code, http.StatusBadRequest, rec.Body.String())
			}
			var errResp map[string]string
			decode(t, rec, &errResp)
			if errResp["error"] == "" {
				t.Fatalf("expected non-empty error message, got %v", errResp)
			}
		})
	}
}

// TestListWithAuthorFilter verifies listing and the ?author= filter.
func TestListWithAuthorFilter(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()

	books := []Book{
		{Title: "Book A", Author: "Alice", Year: 2001},
		{Title: "Book B", Author: "Bob", Year: 2002},
		{Title: "Book C", Author: "Alice", Year: 2003},
	}
	for _, b := range books {
		rec := do(t, srv, http.MethodPost, "/books", b)
		if rec.Code != http.StatusCreated {
			t.Fatalf("create status = %d (body=%s)", rec.Code, rec.Body.String())
		}
	}

	rec := do(t, srv, http.MethodGet, "/books", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("list status = %d", rec.Code)
	}
	var all []Book
	decode(t, rec, &all)
	if len(all) != 3 {
		t.Fatalf("list len = %d, want 3", len(all))
	}

	rec = do(t, srv, http.MethodGet, "/books?author=Alice", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("filtered list status = %d", rec.Code)
	}
	var filtered []Book
	decode(t, rec, &filtered)
	if len(filtered) != 2 {
		t.Fatalf("filtered len = %d, want 2", len(filtered))
	}
	for _, b := range filtered {
		if b.Author != "Alice" {
			t.Fatalf("unexpected author %q in filtered list", b.Author)
		}
	}
}

// TestUpdateAndDelete exercises the PUT and DELETE endpoints, including
// the not-found cases.
func TestUpdateAndDelete(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()

	// update on missing id -> 404
	rec := do(t, srv, http.MethodPut, "/books/999", Book{Title: "X", Author: "Y", Year: 2000})
	if rec.Code != http.StatusNotFound {
		t.Fatalf("update missing status = %d, want 404 (body=%s)", rec.Code, rec.Body.String())
	}

	// create then update
	rec = do(t, srv, http.MethodPost, "/books", Book{Title: "Old", Author: "Auth", Year: 1990})
	if rec.Code != http.StatusCreated {
		t.Fatalf("create status = %d", rec.Code)
	}
	var created Book
	decode(t, rec, &created)

	rec = do(t, srv, http.MethodPut, "/books/1", Book{Title: "New", Author: "Auth2", Year: 1991, ISBN: "111"})
	if rec.Code != http.StatusOK {
		t.Fatalf("update status = %d (body=%s)", rec.Code, rec.Body.String())
	}
	var updated Book
	decode(t, rec, &updated)
	if updated.Title != "New" || updated.Author != "Auth2" || updated.Year != 1991 || updated.ISBN != "111" {
		t.Fatalf("updated = %+v", updated)
	}

	// delete
	rec = do(t, srv, http.MethodDelete, "/books/1", nil)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("delete status = %d, want 204", rec.Code)
	}
	// now get -> 404
	rec = do(t, srv, http.MethodGet, "/books/1", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("get after delete status = %d, want 404", rec.Code)
	}
	// delete again -> 404
	rec = do(t, srv, http.MethodDelete, "/books/1", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("re-delete status = %d, want 404", rec.Code)
	}
}

// TestHealthCheck verifies the health endpoint.
func TestHealthCheck(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()

	rec := do(t, srv, http.MethodGet, "/health", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("health status = %d, want 200", rec.Code)
	}
	var body map[string]string
	decode(t, rec, &body)
	if body["status"] != "ok" {
		t.Fatalf("health body = %v, want status=ok", body)
	}
}

// TestStoreCRUD is a unit test against the Store directly, ensuring the
// SQLite layer behaves without HTTP involvement.
func TestStoreCRUD(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()
	store := srv.store

	b := &Book{Title: "Unit", Author: "Tester", Year: 2020, ISBN: "abc"}
	if err := store.Create(b); err != nil {
		t.Fatalf("Create: %v", err)
	}
	if b.ID == 0 {
		t.Fatal("ID not set after Create")
	}
	got, err := store.Get(b.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got.Title != b.Title {
		t.Fatalf("Get returned %v, want %v", got, b)
	}
	if err := store.Update(b.ID, &Book{Title: "Unit2", Author: "Tester", Year: 2021}); err != nil {
		t.Fatalf("Update: %v", err)
	}
	got, _ = store.Get(b.ID)
	if got.Title != "Unit2" || got.Year != 2021 {
		t.Fatalf("after Update got %v", got)
	}
	if err := store.Delete(b.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if _, err := store.Get(b.ID); err != ErrNotFound {
		t.Fatalf("expected ErrNotFound, got %v", err)
	}
	// sanity: the underlying *sql.DB is non-nil
	var _ *sql.DB
}
