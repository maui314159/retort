package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func newTestServer(t *testing.T) *Server {
	store := newTestStore(t)
	return NewServer(store)
}

func doRequest(t *testing.T, srv *Server, method, target string, body any) *httptest.ResponseRecorder {
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
	srv.ServeHTTP(rec, req)
	return rec
}

func TestHealthEndpoint(t *testing.T) {
	srv := newTestServer(t)
	rec := doRequest(t, srv, http.MethodGet, "/health", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", rec.Code, rec.Body.String())
	}
	var resp map[string]string
	if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if resp["status"] != "ok" {
		t.Fatalf("expected status ok, got %q", resp["status"])
	}
}

func TestCreateBook_ValidationErrors(t *testing.T) {
	srv := newTestServer(t)

	cases := []struct {
		name string
		body map[string]any
		want int
	}{
		{"missing title", map[string]any{"author": "x", "year": 2020}, http.StatusBadRequest},
		{"missing author", map[string]any{"title": "x", "year": 2020}, http.StatusBadRequest},
		{"empty title", map[string]any{"title": "  ", "author": "x"}, http.StatusBadRequest},
		{"bad year", map[string]any{"title": "t", "author": "a", "year": 99999}, http.StatusBadRequest},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			rec := doRequest(t, srv, http.MethodPost, "/books", c.body)
			if rec.Code != c.want {
				t.Fatalf("expected %d, got %d: %s", c.want, rec.Code, rec.Body.String())
			}
		})
	}
}

func TestBookLifecycle(t *testing.T) {
	srv := newTestServer(t)

	// Create
	rec := doRequest(t, srv, http.MethodPost, "/books", map[string]any{
		"title": "T1", "author": "A1", "year": 2021, "isbn": "i1",
	})
	if rec.Code != http.StatusCreated {
		t.Fatalf("create: expected 201, got %d: %s", rec.Code, rec.Body.String())
	}
	var created Book
	if err := json.Unmarshal(rec.Body.Bytes(), &created); err != nil {
		t.Fatalf("decode created: %v", err)
	}
	if created.ID == 0 || created.Title != "T1" {
		t.Fatalf("unexpected created book: %+v", created)
	}

	// Get
	rec = doRequest(t, srv, http.MethodGet, "/books/1", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("get: expected 200, got %d", rec.Code)
	}

	// Get missing
	rec = doRequest(t, srv, http.MethodGet, "/books/9999", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("get missing: expected 404, got %d", rec.Code)
	}

	// Get bad id
	rec = doRequest(t, srv, http.MethodGet, "/books/abc", nil)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("get bad id: expected 400, got %d", rec.Code)
	}

	// List all
	rec = doRequest(t, srv, http.MethodGet, "/books", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("list: expected 200, got %d", rec.Code)
	}
	var list []Book
	if err := json.Unmarshal(rec.Body.Bytes(), &list); err != nil {
		t.Fatalf("decode list: %v", err)
	}
	if len(list) != 1 {
		t.Fatalf("expected 1 book, got %d", len(list))
	}

	// List with filter returns empty array (not null)
	rec = doRequest(t, srv, http.MethodGet, "/books?author=Nope", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("list filter: expected 200, got %d", rec.Code)
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &list); err != nil {
		t.Fatalf("decode filtered list: %v", err)
	}
	if len(list) != 0 {
		t.Fatalf("expected empty filtered list, got %d", len(list))
	}

	// Update
	rec = doRequest(t, srv, http.MethodPut, "/books/1", map[string]any{
		"title": "T2", "author": "A2", "year": 2022, "isbn": "i2",
	})
	if rec.Code != http.StatusOK {
		t.Fatalf("update: expected 200, got %d: %s", rec.Code, rec.Body.String())
	}
	var updated Book
	if err := json.Unmarshal(rec.Body.Bytes(), &updated); err != nil {
		t.Fatalf("decode updated: %v", err)
	}
	if updated.Title != "T2" || updated.Author != "A2" {
		t.Fatalf("unexpected updated book: %+v", updated)
	}

	// Update missing
	rec = doRequest(t, srv, http.MethodPut, "/books/9999", map[string]any{
		"title": "T", "author": "A", "year": 1,
	})
	if rec.Code != http.StatusNotFound {
		t.Fatalf("update missing: expected 404, got %d", rec.Code)
	}

	// Delete
	rec = doRequest(t, srv, http.MethodDelete, "/books/1", nil)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("delete: expected 204, got %d", rec.Code)
	}

	// Delete again -> 404
	rec = doRequest(t, srv, http.MethodDelete, "/books/1", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("delete again: expected 404, got %d", rec.Code)
	}
}

func TestMethodNotAllowed(t *testing.T) {
	srv := newTestServer(t)
	rec := doRequest(t, srv, http.MethodPatch, "/books/1", nil)
	if rec.Code != http.StatusMethodNotAllowed && rec.Code != http.StatusNotFound {
		t.Fatalf("unexpected status for unsupported method: %d", rec.Code)
	}
}
