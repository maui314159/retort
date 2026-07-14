package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"testing"
)

// newTestServer returns a Server backed by an in-file SQLite database
// located in the test's temp directory.
func newTestServer(t *testing.T) *Server {
	t.Helper()
	dir := t.TempDir()
	store, err := NewStore(dir + "/test.db")
	if err != nil {
		t.Fatalf("new store: %v", err)
	}
	t.Cleanup(func() { _ = store.Close() })
	return NewServer(store)
}

func decode[T any](t *testing.T, body []byte) T {
	t.Helper()
	var v T
	if err := json.Unmarshal(body, &v); err != nil {
		t.Fatalf("decode: %v body=%s", err, body)
	}
	return v
}

// TestCreateAndGetBook verifies the create -> get round trip and the
// required-field validation.
func TestCreateAndGetBook(t *testing.T) {
	srv := newTestServer(t)

	// Missing title should be rejected.
	req := httptest.NewRequest(http.MethodPost, "/books", strings.NewReader(`{"author":"Asimov"}`))
	rec := httptest.NewRecorder()
	srv.ServeHTTP(rec, req)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 for missing title, got %d", rec.Code)
	}

	// Valid create.
	body := `{"title":"Foundation","author":"Isaac Asimov","year":1951,"isbn":"0-553-29335-4"}`
	req = httptest.NewRequest(http.MethodPost, "/books", strings.NewReader(body))
	rec = httptest.NewRecorder()
	srv.ServeHTTP(rec, req)
	if rec.Code != http.StatusCreated {
		t.Fatalf("expected 201, got %d body=%s", rec.Code, rec.Body.String())
	}
	created := decode[Book](t, rec.Body.Bytes())
	if created.Title != "Foundation" || created.ID == 0 {
		t.Fatalf("unexpected created book: %+v", created)
	}

	// Fetch it back.
	req = httptest.NewRequest(http.MethodGet, "/books/"+strconv.FormatInt(created.ID, 10), nil)
	rec = httptest.NewRecorder()
	srv.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
	got := decode[Book](t, rec.Body.Bytes())
	if got.ISBN != "0-553-29335-4" {
		t.Fatalf("unexpected isbn: %s", got.ISBN)
	}

	// Unknown id -> 404.
	req = httptest.NewRequest(http.MethodGet, "/books/999999", nil)
	rec = httptest.NewRecorder()
	srv.ServeHTTP(rec, req)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", rec.Code)
	}
}

// TestListWithAuthorFilter checks listing and the ?author= query filter.
func TestListWithAuthorFilter(t *testing.T) {
	srv := newTestServer(t)

	for _, b := range []string{
		`{"title":"The Hobbit","author":"Tolkien"}`,
		`{"title":"Dune","author":"Herbert"}`,
		`{"title":"LOTR","author":"Tolkien"}`,
	} {
		req := httptest.NewRequest(http.MethodPost, "/books", strings.NewReader(b))
		rec := httptest.NewRecorder()
		srv.ServeHTTP(rec, req)
		if rec.Code != http.StatusCreated {
			t.Fatalf("create failed: %d", rec.Code)
		}
	}

	// All books.
	req := httptest.NewRequest(http.MethodGet, "/books", nil)
	rec := httptest.NewRecorder()
	srv.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
	all := decode[[]*Book](t, rec.Body.Bytes())
	if len(all) != 3 {
		t.Fatalf("expected 3 books, got %d", len(all))
	}

	// Filter by author.
	req = httptest.NewRequest(http.MethodGet, "/books?author=Tolkien", nil)
	rec = httptest.NewRecorder()
	srv.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
	filtered := decode[[]*Book](t, rec.Body.Bytes())
	if len(filtered) != 2 {
		t.Fatalf("expected 2 Tolkien books, got %d", len(filtered))
	}
	for _, b := range filtered {
		if b.Author != "Tolkien" {
			t.Fatalf("unexpected author: %s", b.Author)
		}
	}
}

// TestUpdateAndDelete exercises PUT and DELETE plus status codes.
func TestUpdateAndDelete(t *testing.T) {
	srv := newTestServer(t)

	req := httptest.NewRequest(http.MethodPost, "/books", strings.NewReader(`{"title":"Old","author":"A"}`))
	rec := httptest.NewRecorder()
	srv.ServeHTTP(rec, req)
	if rec.Code != http.StatusCreated {
		t.Fatalf("create failed: %d", rec.Code)
	}
	created := decode[Book](t, rec.Body.Bytes())

	// Update with valid data.
	req = httptest.NewRequest(http.MethodPut, "/books/"+strconv.FormatInt(created.ID, 10),
		bytes.NewReader([]byte(`{"title":"New","author":"B","year":2020}`)))
	rec = httptest.NewRecorder()
	srv.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200 on update, got %d", rec.Code)
	}
	updated := decode[Book](t, rec.Body.Bytes())
	if updated.Title != "New" || updated.Author != "B" || updated.Year != 2020 {
		t.Fatalf("unexpected updated: %+v", updated)
	}
	if updated.CreatedAt != created.CreatedAt {
		t.Fatalf("created_at should not change on update")
	}

	// Update with missing author -> 400.
	req = httptest.NewRequest(http.MethodPut, "/books/"+strconv.FormatInt(created.ID, 10),
		strings.NewReader(`{"title":"New"}`))
	rec = httptest.NewRecorder()
	srv.ServeHTTP(rec, req)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", rec.Code)
	}

	// Delete.
	req = httptest.NewRequest(http.MethodDelete, "/books/"+strconv.FormatInt(created.ID, 10), nil)
	rec = httptest.NewRecorder()
	srv.ServeHTTP(rec, req)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("expected 204, got %d", rec.Code)
	}

	// Delete again -> 404.
	req = httptest.NewRequest(http.MethodDelete, "/books/"+strconv.FormatInt(created.ID, 10), nil)
	rec = httptest.NewRecorder()
	srv.ServeHTTP(rec, req)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("expected 404 on second delete, got %d", rec.Code)
	}
}

// TestHealthCheck verifies the health endpoint returns 200 ok.
func TestHealthCheck(t *testing.T) {
	srv := newTestServer(t)
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	rec := httptest.NewRecorder()
	srv.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), "ok") {
		t.Fatalf("expected body to contain ok, got %s", rec.Body.String())
	}
}
