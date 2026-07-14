package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"
)

func newTestAPI(t *testing.T) (*API, func()) {
	t.Helper()
	store, err := NewStore(":memory:")
	if err != nil {
		t.Fatalf("new store: %v", err)
	}
	return NewAPI(store), func() { _ = store.Close() }
}

func do(t *testing.T, api *API, method, path string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var buf bytes.Buffer
	if body != nil {
		if err := json.NewEncoder(&buf).Encode(body); err != nil {
			t.Fatalf("encode: %v", err)
		}
	}
	req := httptest.NewRequest(method, path, &buf)
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()
	api.ServeHTTP(rr, req)
	return rr
}

func TestCreateListGetDelete(t *testing.T) {
	api, cleanup := newTestAPI(t)
	defer cleanup()

	// Create
	rr := do(t, api, "POST", "/books", map[string]any{
		"title":  "The Go Programming Language",
		"author": "Donovan & Kernighan",
		"year":   2015,
		"isbn":   "978-0134190440",
	})
	if rr.Code != http.StatusCreated {
		t.Fatalf("create status = %d, body=%s", rr.Code, rr.Body.String())
	}
	var created Book
	if err := json.Unmarshal(rr.Body.Bytes(), &created); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if created.ID == 0 || created.Title != "The Go Programming Language" {
		t.Fatalf("unexpected book: %+v", created)
	}

	// Get
	rr = do(t, api, "GET", "/books/1", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("get status = %d, body=%s", rr.Code, rr.Body.String())
	}

	// List all
	rr = do(t, api, "GET", "/books", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("list status = %d", rr.Code)
	}
	var list []*Book
	if err := json.Unmarshal(rr.Body.Bytes(), &list); err != nil {
		t.Fatalf("unmarshal list: %v", err)
	}
	if len(list) != 1 {
		t.Fatalf("expected 1 book, got %d", len(list))
	}

	// List with author filter
	rr = do(t, api, "GET", "/books?author=Donovan%20%26%20Kernighan", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("filter status = %d", rr.Code)
	}
	if err := json.Unmarshal(rr.Body.Bytes(), &list); err != nil {
		t.Fatalf("unmarshal filtered: %v", err)
	}
	if len(list) != 1 {
		t.Fatalf("expected 1 filtered book, got %d", len(list))
	}

	// Delete
	rr = do(t, api, "DELETE", "/books/1", nil)
	if rr.Code != http.StatusNoContent {
		t.Fatalf("delete status = %d, body=%s", rr.Code, rr.Body.String())
	}

	// Get after delete -> 404
	rr = do(t, api, "GET", "/books/1", nil)
	if rr.Code != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", rr.Code)
	}
}

func TestValidationErrors(t *testing.T) {
	api, cleanup := newTestAPI(t)
	defer cleanup()

	// Missing title and author
	rr := do(t, api, "POST", "/books", map[string]any{})
	if rr.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d, body=%s", rr.Code, rr.Body.String())
	}
	var resp struct {
		Error  string            `json:"error"`
		Fields map[string]string `json:"fields"`
	}
	if err := json.Unmarshal(rr.Body.Bytes(), &resp); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if _, ok := resp.Fields["title"]; !ok {
		t.Errorf("expected title field error, got %+v", resp.Fields)
	}
	if _, ok := resp.Fields["author"]; !ok {
		t.Errorf("expected author field error, got %+v", resp.Fields)
	}

	// Invalid id on GET
	rr = do(t, api, "GET", "/books/abc", nil)
	if rr.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 for bad id, got %d", rr.Code)
	}
}

func TestUpdateAndHealth(t *testing.T) {
	api, cleanup := newTestAPI(t)
	defer cleanup()

	rr := do(t, api, "GET", "/health", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("health status = %d", rr.Code)
	}

	// Create then update
	rr = do(t, api, "POST", "/books", map[string]any{
		"title":  "Old Title",
		"author": "Old Author",
	})
	if rr.Code != http.StatusCreated {
		t.Fatalf("create status = %d, body=%s", rr.Code, rr.Body.String())
	}
	var b Book
	if err := json.Unmarshal(rr.Body.Bytes(), &b); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}

	rr = do(t, api, "PUT", "/books/"+itoa(b.ID), map[string]any{
		"title":  "New Title",
		"author": "New Author",
		"year":   2020,
	})
	if rr.Code != http.StatusOK {
		t.Fatalf("update status = %d, body=%s", rr.Code, rr.Body.String())
	}
	var updated Book
	if err := json.Unmarshal(rr.Body.Bytes(), &updated); err != nil {
		t.Fatalf("unmarshal update: %v", err)
	}
	if updated.Title != "New Title" || updated.Author != "New Author" || updated.Year != 2020 {
		t.Fatalf("unexpected updated book: %+v", updated)
	}
	if updated.CreatedAt.IsZero() {
		t.Errorf("expected created_at preserved")
	}

	// Update non-existent -> 404
	rr = do(t, api, "PUT", "/books/9999", map[string]any{
		"title":  "x",
		"author": "y",
	})
	if rr.Code != http.StatusNotFound {
		t.Fatalf("expected 404 for missing update, got %d", rr.Code)
	}
}

func itoa(n int64) string {
	return strconv.FormatInt(n, 10)
}
