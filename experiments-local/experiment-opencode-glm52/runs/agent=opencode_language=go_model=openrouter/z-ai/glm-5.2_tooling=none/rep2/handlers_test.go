package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

// newTestServer spins up a server with an in-memory SQLite database.
func newTestServer(t *testing.T) *server {
	t.Helper()
	srv, err := newServer(":memory:")
	if err != nil {
		t.Fatalf("init server: %v", err)
	}
	t.Cleanup(func() { srv.db.Close() })
	return srv
}

func doRequest(t *testing.T, h http.Handler, method, target string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var buf bytes.Buffer
	if body != nil {
		if err := json.NewEncoder(&buf).Encode(body); err != nil {
			t.Fatalf("encode body: %v", err)
		}
	}
	req := httptest.NewRequest(method, target, &buf)
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)
	return rr
}

// TestCreateAndGetBook verifies the create -> fetch flow with a valid body.
func TestCreateAndGetBook(t *testing.T) {
	srv := newTestServer(t)
	h := srv.routes()

	rr := doRequest(t, h, http.MethodPost, "/books", map[string]any{
		"title":  "The Go Programming Language",
		"author": "Donovan",
		"year":   2015,
		"isbn":   "978-0134190440",
	})
	if rr.Code != http.StatusCreated {
		t.Fatalf("create: want 201, got %d (%s)", rr.Code, rr.Body.String())
	}
	var created Book
	if err := json.Unmarshal(rr.Body.Bytes(), &created); err != nil {
		t.Fatalf("decode created: %v", err)
	}
	if created.ID == 0 {
		t.Fatalf("expected non-zero id")
	}
	if created.Title != "The Go Programming Language" {
		t.Fatalf("unexpected title: %q", created.Title)
	}

	rr = doRequest(t, h, http.MethodGet, "/books/1", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("get: want 200, got %d", rr.Code)
	}
	var got Book
	if err := json.Unmarshal(rr.Body.Bytes(), &got); err != nil {
		t.Fatalf("decode got: %v", err)
	}
	if got.ID != created.ID || got.Title != created.Title {
		t.Fatalf("mismatch: %+v vs %+v", got, created)
	}
}

// TestCreateValidation verifies the server rejects bodies missing required
// fields (title and author are required).
func TestCreateValidation(t *testing.T) {
	srv := newTestServer(t)
	h := srv.routes()

	cases := []struct {
		name string
		body map[string]any
	}{
		{"missing both", map[string]any{"year": 2020}},
		{"missing author", map[string]any{"title": "X"}},
		{"missing title", map[string]any{"author": "Y"}},
		{"empty title", map[string]any{"title": "", "author": "Y"}},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			rr := doRequest(t, h, http.MethodPost, "/books", tc.body)
			if rr.Code != http.StatusBadRequest {
				t.Fatalf("want 400, got %d (%s)", rr.Code, rr.Body.String())
			}
		})
	}
}

// TestListWithAuthorFilter verifies the GET /books?author= query filter.
func TestListWithAuthorFilter(t *testing.T) {
	srv := newTestServer(t)
	h := srv.routes()

	for _, b := range []map[string]any{
		{"title": "A", "author": "Alice", "year": 2001, "isbn": "i1"},
		{"title": "B", "author": "Bob", "year": 2002, "isbn": "i2"},
		{"title": "C", "author": "Alice", "year": 2003, "isbn": "i3"},
	} {
		rr := doRequest(t, h, http.MethodPost, "/books", b)
		if rr.Code != http.StatusCreated {
			t.Fatalf("seed: want 201, got %d (%s)", rr.Code, rr.Body.String())
		}
	}

	// All
	rr := doRequest(t, h, http.MethodGet, "/books", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("list all: want 200, got %d", rr.Code)
	}
	var all []Book
	if err := json.Unmarshal(rr.Body.Bytes(), &all); err != nil {
		t.Fatalf("decode all: %v", err)
	}
	if len(all) != 3 {
		t.Fatalf("list all: want 3 books, got %d", len(all))
	}

	// Alice only
	rr = doRequest(t, h, http.MethodGet, "/books?author=Alice", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("list filter: want 200, got %d", rr.Code)
	}
	var filtered []Book
	if err := json.Unmarshal(rr.Body.Bytes(), &filtered); err != nil {
		t.Fatalf("decode filtered: %v", err)
	}
	if len(filtered) != 2 {
		t.Fatalf("list filter: want 2 books, got %d (%s)", len(filtered), rr.Body.String())
	}
	for _, b := range filtered {
		if b.Author != "Alice" {
			t.Fatalf("unexpected author: %q", b.Author)
		}
	}
}

// TestUpdateAndDeleteBook covers the PUT and DELETE lifecycle.
func TestUpdateAndDeleteBook(t *testing.T) {
	srv := newTestServer(t)
	h := srv.routes()

	rr := doRequest(t, h, http.MethodPost, "/books", map[string]any{
		"title": "Old", "author": "OldA", "year": 1999, "isbn": "x",
	})
	if rr.Code != http.StatusCreated {
		t.Fatalf("create: want 201, got %d (%s)", rr.Code, rr.Body.String())
	}

	// Update
	rr = doRequest(t, h, http.MethodPut, "/books/1", map[string]any{
		"title": "New", "author": "NewA", "year": 2024, "isbn": "y",
	})
	if rr.Code != http.StatusOK {
		t.Fatalf("update: want 200, got %d (%s)", rr.Code, rr.Body.String())
	}
	var updated Book
	if err := json.Unmarshal(rr.Body.Bytes(), &updated); err != nil {
		t.Fatalf("decode updated: %v", err)
	}
	if updated.Title != "New" || updated.Author != "NewA" || updated.Year != 2024 {
		t.Fatalf("unexpected updated: %+v", updated)
	}

	// Get reflects update
	rr = doRequest(t, h, http.MethodGet, "/books/1", nil)
	var got Book
	_ = json.Unmarshal(rr.Body.Bytes(), &got)
	if got.Title != "New" {
		t.Fatalf("expected updated title, got %q", got.Title)
	}

	// Delete
	rr = doRequest(t, h, http.MethodDelete, "/books/1", nil)
	if rr.Code != http.StatusNoContent {
		t.Fatalf("delete: want 204, got %d (%s)", rr.Code, rr.Body.String())
	}

	// Get after delete -> 404
	rr = doRequest(t, h, http.MethodGet, "/books/1", nil)
	if rr.Code != http.StatusNotFound {
		t.Fatalf("get after delete: want 404, got %d", rr.Code)
	}

	// Delete missing -> 404
	rr = doRequest(t, h, http.MethodDelete, "/books/999", nil)
	if rr.Code != http.StatusNotFound {
		t.Fatalf("delete missing: want 404, got %d", rr.Code)
	}
}

// TestHealthCheck verifies the /health endpoint.
func TestHealthCheck(t *testing.T) {
	srv := newTestServer(t)
	h := srv.routes()

	rr := doRequest(t, h, http.MethodGet, "/health", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("want 200, got %d", rr.Code)
	}
	var resp map[string]string
	if err := json.Unmarshal(rr.Body.Bytes(), &resp); err != nil {
		t.Fatalf("decode health: %v", err)
	}
	if resp["status"] != "ok" {
		t.Fatalf("unexpected status: %q", resp["status"])
	}
}

// TestInvalidJSONBody ensures malformed JSON returns 400.
func TestInvalidJSONBody(t *testing.T) {
	srv := newTestServer(t)
	h := srv.routes()

	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBufferString("{not json"))
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)
	if rr.Code != http.StatusBadRequest {
		t.Fatalf("want 400, got %d", rr.Code)
	}
}
