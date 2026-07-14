package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"
)

// newTestAPI returns an API backed by an in-memory SQLite database and a
// cleanup function.
func newTestAPI(t *testing.T) (*API, func()) {
	t.Helper()
	store, err := NewStore("file::memory:?cache=shared")
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	cleanup := func() {
		_ = store.Close()
	}
	return NewAPI(store), cleanup
}

func do(t *testing.T, api *API, method, target string, body any) *httptest.ResponseRecorder {
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
	api.Handler().ServeHTTP(rr, req)
	return rr
}

// TestCreateAndGetBook verifies a book can be created and then retrieved by id.
func TestCreateAndGetBook(t *testing.T) {
	api, cleanup := newTestAPI(t)
	defer cleanup()

	rr := do(t, api, http.MethodPost, "/books", map[string]any{
		"title":  "The Go Programming Language",
		"author": "Alan Donovan",
		"year":   2015,
		"isbn":   "978-0134190440",
	})
	if rr.Code != http.StatusCreated {
		t.Fatalf("create: expected 201, got %d (body=%s)", rr.Code, rr.Body.String())
	}
	var created Book
	if err := json.NewDecoder(rr.Body).Decode(&created); err != nil {
		t.Fatalf("decode created: %v", err)
	}
	if created.ID == 0 || created.Title != "The Go Programming Language" {
		t.Fatalf("unexpected created book: %+v", created)
	}

	rr = do(t, api, http.MethodGet, "/books/"+itoa(created.ID), nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("get: expected 200, got %d", rr.Code)
	}
	var got Book
	if err := json.NewDecoder(rr.Body).Decode(&got); err != nil {
		t.Fatalf("decode got: %v", err)
	}
	if got.ID != created.ID || got.Author != "Alan Donovan" {
		t.Fatalf("unexpected fetched book: %+v", got)
	}
}

// TestValidationRejectsMissingFields ensures that omitting required fields
// returns a 400 with validation details.
func TestValidationRejectsMissingFields(t *testing.T) {
	api, cleanup := newTestAPI(t)
	defer cleanup()

	rr := do(t, api, http.MethodPost, "/books", map[string]any{
		"year": 2000,
	})
	if rr.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d (body=%s)", rr.Code, rr.Body.String())
	}
	var resp struct {
		Error   string   `json:"error"`
		Details []string `json:"details"`
	}
	if err := json.NewDecoder(rr.Body).Decode(&resp); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if len(resp.Details) != 2 {
		t.Fatalf("expected 2 validation errors, got %v", resp.Details)
	}
}

// TestAuthorFilter verifies the ?author= query filter narrows the list.
func TestAuthorFilter(t *testing.T) {
	api, cleanup := newTestAPI(t)
	defer cleanup()

	for _, b := range []map[string]any{
		{"title": "Book A", "author": "Alice"},
		{"title": "Book B", "author": "Bob"},
		{"title": "Book C", "author": "Alice"},
	} {
		rr := do(t, api, http.MethodPost, "/books", b)
		if rr.Code != http.StatusCreated {
			t.Fatalf("create: expected 201, got %d", rr.Code)
		}
	}

	rr := do(t, api, http.MethodGet, "/books?author=Alice", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("list: expected 200, got %d", rr.Code)
	}
	var resp struct {
		Books []*Book `json:"books"`
	}
	if err := json.NewDecoder(rr.Body).Decode(&resp); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if len(resp.Books) != 2 {
		t.Fatalf("expected 2 Alice books, got %d", len(resp.Books))
	}
	for _, b := range resp.Books {
		if b.Author != "Alice" {
			t.Fatalf("unexpected author in filtered list: %q", b.Author)
		}
	}
}

// TestUpdateAndDelete exercises the update and delete lifecycle.
func TestUpdateAndDelete(t *testing.T) {
	api, cleanup := newTestAPI(t)
	defer cleanup()

	rr := do(t, api, http.MethodPost, "/books", map[string]any{
		"title": "Old Title", "author": "Old Author",
	})
	if rr.Code != http.StatusCreated {
		t.Fatalf("create: %d", rr.Code)
	}
	var created Book
	json.NewDecoder(rr.Body).Decode(&created)

	rr = do(t, api, http.MethodPut, "/books/"+itoa(created.ID), map[string]any{
		"title": "New Title", "author": "New Author", "year": 2024,
	})
	if rr.Code != http.StatusOK {
		t.Fatalf("update: expected 200, got %d (body=%s)", rr.Code, rr.Body.String())
	}
	var updated Book
	json.NewDecoder(rr.Body).Decode(&updated)
	if updated.Title != "New Title" || updated.Author != "New Author" || updated.Year != 2024 {
		t.Fatalf("unexpected updated book: %+v", updated)
	}
	if updated.CreatedAt != created.CreatedAt {
		t.Fatalf("created_at should be preserved")
	}

	rr = do(t, api, http.MethodDelete, "/books/"+itoa(created.ID), nil)
	if rr.Code != http.StatusNoContent {
		t.Fatalf("delete: expected 204, got %d", rr.Code)
	}

	rr = do(t, api, http.MethodGet, "/books/"+itoa(created.ID), nil)
	if rr.Code != http.StatusNotFound {
		t.Fatalf("get after delete: expected 404, got %d", rr.Code)
	}
}

// TestHealth verifies the health endpoint responds 200 with status ok.
func TestHealth(t *testing.T) {
	api, cleanup := newTestAPI(t)
	defer cleanup()

	rr := do(t, api, http.MethodGet, "/health", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("health: expected 200, got %d", rr.Code)
	}
	var resp map[string]string
	if err := json.NewDecoder(rr.Body).Decode(&resp); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if resp["status"] != "ok" {
		t.Fatalf("health status = %q, want ok", resp["status"])
	}
}

// TestGetInvalidID checks that a non-numeric id returns 400.
func TestGetInvalidID(t *testing.T) {
	api, cleanup := newTestAPI(t)
	defer cleanup()

	rr := do(t, api, http.MethodGet, "/books/abc", nil)
	if rr.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", rr.Code)
	}
}

func itoa(n int64) string {
	return strconv.FormatInt(n, 10)
}
