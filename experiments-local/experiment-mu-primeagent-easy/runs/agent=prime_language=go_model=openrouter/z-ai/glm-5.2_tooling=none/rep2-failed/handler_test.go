package main

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"
)

// newTestServer creates an in-process test server backed by a fresh
// in-memory SQLite database. The returned cleanup function must be
// called when the test is done.
func newTestServer(t *testing.T) (*httptest.Server, func()) {
	t.Helper()
	store, err := NewStore(":memory:")
	if err != nil {
		t.Fatalf("new store: %v", err)
	}
	mux := http.NewServeMux()
	NewHandler(store).Routes(mux)
	srv := httptest.NewServer(mux)
	return srv, func() {
		srv.Close()
		_ = store.Close()
	}
}

// doJSON performs a request with a JSON body (or nil) and returns the
// status code and decoded body. The body is decoded into an any so
// that both JSON objects (map[string]any) and arrays ([]any) are
// handled.
func doJSON(t *testing.T, srv *httptest.Server, method, path string, body any) (int, any) {
	t.Helper()
	var rdr io.Reader
	if body != nil {
		b, err := json.Marshal(body)
		if err != nil {
			t.Fatalf("marshal: %v", err)
		}
		rdr = bytes.NewReader(b)
	}
	req, err := http.NewRequest(method, srv.URL+path, rdr)
	if err != nil {
		t.Fatalf("new request: %v", err)
	}
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("do: %v", err)
	}
	defer resp.Body.Close()
	data, _ := io.ReadAll(resp.Body)
	var out any
	if len(data) > 0 {
		_ = json.Unmarshal(data, &out)
	}
	return resp.StatusCode, out
}

// bodyMap is a helper that type-asserts a decoded body into a map.
func bodyMap(t *testing.T, v any) map[string]any {
	t.Helper()
	m, ok := v.(map[string]any)
	if !ok {
		t.Fatalf("expected JSON object, got %T: %v", v, v)
	}
	return m
}

// bodyArray is a helper that type-asserts a decoded body into a slice.
func bodyArray(t *testing.T, v any) []any {
	t.Helper()
	a, ok := v.([]any)
	if !ok {
		t.Fatalf("expected JSON array, got %T: %v", v, v)
	}
	return a
}

// Test 1: health endpoint returns 200 and {"status":"ok"}.
func TestHealth(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()

	code, raw := doJSON(t, srv, "GET", "/health", nil)
	if code != http.StatusOK {
		t.Fatalf("expected 200, got %d", code)
	}
	body := bodyMap(t, raw)
	if body["status"] != "ok" {
		t.Fatalf("expected status ok, got %v", body)
	}
}

// Test 2: create book then retrieve it by ID.
func TestCreateAndGetBook(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()

	// Create
	code, raw := doJSON(t, srv, "POST", "/books", map[string]any{
		"title":  "The Go Programming Language",
		"author": "Alan Donovan",
		"year":   2015,
		"isbn":   "978-0134190440",
	})
	if code != http.StatusCreated {
		t.Fatalf("expected 201, got %d: %v", code, raw)
	}
	body := bodyMap(t, raw)
	id, ok := body["id"].(float64)
	if !ok || id == 0 {
		t.Fatalf("expected non-zero id, got %v", body)
	}

	// Retrieve
	code2, raw2 := doJSON(t, srv, "GET", "/books/"+itoa(int64(id)), nil)
	if code2 != http.StatusOK {
		t.Fatalf("expected 200, got %d: %v", code2, raw2)
	}
	body2 := bodyMap(t, raw2)
	if body2["title"] != "The Go Programming Language" {
		t.Fatalf("unexpected title: %v", body2)
	}
	if body2["author"] != "Alan Donovan" {
		t.Fatalf("unexpected author: %v", body2)
	}
}

// Test 3: validation — missing title and author yields 400.
func TestCreateValidation(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()

	cases := []struct {
		name string
		body map[string]any
	}{
		{"missing title", map[string]any{"author": "X", "year": 2000}},
		{"missing author", map[string]any{"title": "Y", "year": 2000}},
		{"both missing", map[string]any{"year": 2000}},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			code, raw := doJSON(t, srv, "POST", "/books", tc.body)
			if code != http.StatusBadRequest {
				t.Fatalf("expected 400, got %d: %v", code, raw)
			}
		})
	}
}

// Test 4: list books with author filter.
func TestListWithAuthorFilter(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()

	// Seed two books by different authors and one by the same author.
	seed := []map[string]any{
		{"title": "A", "author": "Alice", "year": 2001},
		{"title": "B", "author": "Bob", "year": 2002},
		{"title": "C", "author": "Alice", "year": 2003},
	}
	for _, b := range seed {
		if code, _ := doJSON(t, srv, "POST", "/books", b); code != http.StatusCreated {
			t.Fatalf("seed failed: %d", code)
		}
	}

	// No filter → 3 books.
	code, raw := doJSON(t, srv, "GET", "/books", nil)
	if code != http.StatusOK {
		t.Fatalf("expected 200, got %d", code)
	}
	all := bodyArray(t, raw)
	if len(all) != 3 {
		t.Fatalf("expected 3 items, got %d", len(all))
	}

	// Filter by Alice → 2 books.
	code2, raw2 := doJSON(t, srv, "GET", "/books?author=Alice", nil)
	if code2 != http.StatusOK {
		t.Fatalf("expected 200, got %d", code2)
	}
	alice := bodyArray(t, raw2)
	if len(alice) != 2 {
		t.Fatalf("expected 2 items for Alice, got %d: %v", len(alice), alice)
	}
}

// Test 5: update a book, then verify the changes are persisted.
func TestUpdateBook(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()

	code, raw := doJSON(t, srv, "POST", "/books", map[string]any{
		"title":  "Old Title",
		"author": "Old Author",
		"year":   2000,
	})
	if code != http.StatusCreated {
		t.Fatalf("create failed: %d", code)
	}
	body := bodyMap(t, raw)
	id := itoa(int64(body["id"].(float64)))

	// Update
	code2, raw2 := doJSON(t, srv, "PUT", "/books/"+id, map[string]any{
		"title":  "New Title",
		"author": "New Author",
		"year":   2010,
	})
	if code2 != http.StatusOK {
		t.Fatalf("expected 200 on update, got %d: %v", code2, raw2)
	}
	body2 := bodyMap(t, raw2)
	if body2["title"] != "New Title" {
		t.Fatalf("expected updated title, got %v", body2)
	}

	// Verify
	code3, raw3 := doJSON(t, srv, "GET", "/books/"+id, nil)
	if code3 != http.StatusOK {
		t.Fatalf("expected 200 on get, got %d", code3)
	}
	body3 := bodyMap(t, raw3)
	if body3["author"] != "New Author" {
		t.Fatalf("expected updated author, got %v", body3)
	}
}

// Test 6: delete a book then confirm it's gone (404 on subsequent get).
func TestDeleteBook(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()

	code, raw := doJSON(t, srv, "POST", "/books", map[string]any{
		"title":  "Delete Me",
		"author": "Author",
		"year":   2005,
	})
	if code != http.StatusCreated {
		t.Fatalf("create failed: %d", code)
	}
	body := bodyMap(t, raw)
	id := itoa(int64(body["id"].(float64)))

	// Delete
	req, _ := http.NewRequest("DELETE", srv.URL+"/books/"+id, nil)
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("delete: %v", err)
	}
	resp.Body.Close()
	if resp.StatusCode != http.StatusNoContent {
		t.Fatalf("expected 204 on delete, got %d", resp.StatusCode)
	}

	// Second delete → 404
	req2, _ := http.NewRequest("DELETE", srv.URL+"/books/"+id, nil)
	resp2, err := http.DefaultClient.Do(req2)
	if err != nil {
		t.Fatalf("delete2: %v", err)
	}
	resp2.Body.Close()
	if resp2.StatusCode != http.StatusNotFound {
		t.Fatalf("expected 404 on second delete, got %d", resp2.StatusCode)
	}

	// Get deleted → 404
	code3, _ := doJSON(t, srv, "GET", "/books/"+id, nil)
	if code3 != http.StatusNotFound {
		t.Fatalf("expected 404 for deleted book, got %d", code3)
	}
}

// Test 7: get a non-existent book returns 404.
func TestGetNotFound(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()

	code, _ := doJSON(t, srv, "GET", "/books/99999", nil)
	if code != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", code)
	}
}

// Test 8: invalid id returns 400.
func TestInvalidID(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()

	code, _ := doJSON(t, srv, "GET", "/books/abc", nil)
	if code != http.StatusBadRequest {
		t.Fatalf("expected 400 for non-numeric id, got %d", code)
	}
}

// Test 9: empty list returns an empty JSON array, not null.
func TestEmptyListReturnsArray(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()

	resp, err := http.Get(srv.URL + "/books")
	if err != nil {
		t.Fatalf("get: %v", err)
	}
	defer resp.Body.Close()
	data, _ := io.ReadAll(resp.Body)
	if string(data) != "[]" && string(data) != "[]\n" {
		t.Fatalf("expected empty array, got %q", string(data))
	}
}

// --- helpers ----------------------------------------------------------

func itoa(n int64) string {
	return strconv.FormatInt(n, 10)
}
