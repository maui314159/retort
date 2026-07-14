package main

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strconv"
	"testing"
)

// newTestServer wires up a fresh API backed by an isolated SQLite file in a
// per-test temp directory and returns a running httptest.Server.
func newTestServer(t *testing.T) *httptest.Server {
	t.Helper()
	dbPath := filepath.Join(t.TempDir(), "books.db")

	store, err := openStore(context.Background(), dbPath)
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	t.Cleanup(func() { store.Close() })

	mux := http.NewServeMux()
	newAPI(store).routes(mux)
	return httptest.NewServer(mux)
}

// do is a small helper around http.Do that returns the decoded body (if any)
// alongside the status code.
func do(t *testing.T, method, url string, body any) (int, map[string]any) {
	t.Helper()
	var reqBody io.Reader
	if body != nil {
		raw, err := json.Marshal(body)
		if err != nil {
			t.Fatalf("marshal body: %v", err)
		}
		reqBody = bytes.NewReader(raw)
	}
	req, err := http.NewRequest(method, url, reqBody)
	if err != nil {
		t.Fatalf("new request: %v", err)
	}
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("do request: %v", err)
	}
	defer resp.Body.Close()
	data, _ := io.ReadAll(resp.Body)
	var out map[string]any
	if len(data) > 0 {
		_ = json.Unmarshal(data, &out)
	}
	return resp.StatusCode, out
}

// TestHealthAndCreateGet exercises health, create, and get-by-id end to end.
func TestHealthAndCreateGet(t *testing.T) {
	srv := newTestServer(t)
	defer srv.Close()

	if code, body := do(t, http.MethodGet, srv.URL+"/health", nil); code != http.StatusOK || body["status"] != "ok" {
		t.Fatalf("health: status=%d body=%v", code, body)
	}

	payload := map[string]any{
		"title":  "The Go Programming Language",
		"author": "Donovan & Kernighan",
		"year":   2015,
		"isbn":   "978-0134190440",
	}
	code, body := do(t, http.MethodPost, srv.URL+"/books", payload)
	if code != http.StatusCreated {
		t.Fatalf("create: expected 201, got %d body=%v", code, body)
	}
	if body["title"] != payload["title"] {
		t.Fatalf("create: title mismatch got %v", body["title"])
	}
	id, _ := body["id"].(float64)
	if id <= 0 {
		t.Fatalf("create: missing/invalid id %v", body["id"])
	}

	code, body = do(t, http.MethodGet, srv.URL+"/books/"+strconv.Itoa(int(id)), nil)
	if code != http.StatusOK {
		t.Fatalf("get: expected 200, got %d", code)
	}
	if body["isbn"] != payload["isbn"] {
		t.Fatalf("get: isbn mismatch got %v", body["isbn"])
	}
}

// TestValidationAndListFilter covers required-field validation and the
// ?author= query filter.
func TestValidationAndListFilter(t *testing.T) {
	srv := newTestServer(t)
	defer srv.Close()

	// Missing required fields -> 400.
	for _, bad := range []map[string]any{
		{"author": "No Title"},
		{"title": "No Author"},
		{},
	} {
		if code, _ := do(t, http.MethodPost, srv.URL+"/books", bad); code != http.StatusBadRequest {
			t.Fatalf("validation: expected 400 for %v, got %d", bad, code)
		}
	}

	// Malformed JSON body -> 400.
	req, _ := http.NewRequest(http.MethodPost, srv.URL+"/books", bytes.NewReader([]byte("{not json")))
	req.Header.Set("Content-Type", "application/json")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("bad json request: %v", err)
	}
	resp.Body.Close()
	if resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("malformed json: expected 400, got %d", resp.StatusCode)
	}

	// Create two books by different authors.
	mustCreate(t, srv, "Book A", "Alice", 2001, "111")
	mustCreate(t, srv, "Book B", "Bob", 2002, "222")

	// No filter -> 2 books.
	if n := arrayLen(t, srv.URL+"/books"); n != 2 {
		t.Fatalf("list all: expected 2 books, got %d", n)
	}

	// Filter by author=Alice -> 1 book.
	if n := arrayLen(t, srv.URL+"/books?author=Alice"); n != 1 {
		t.Fatalf("list filter: expected 1 book for Alice, got %d", n)
	}
	// Unknown author -> 0 books (empty JSON array, not null).
	if n := arrayLen(t, srv.URL+"/books?author=Nobody"); n != 0 {
		t.Fatalf("list filter: expected 0 books for Nobody, got %d", n)
	}
}

// arrayLen fetches url and returns the length of the JSON array in the body.
func arrayLen(t *testing.T, url string) int {
	t.Helper()
	resp, err := http.Get(url)
	if err != nil {
		t.Fatalf("get %s: %v", url, err)
	}
	defer resp.Body.Close()
	var arr []any
	if err := json.NewDecoder(resp.Body).Decode(&arr); err != nil {
		t.Fatalf("decode array: %v", err)
	}
	return len(arr)
}

// mustCreate is a helper that fails the test if a book cannot be created.
func mustCreate(t *testing.T, srv *httptest.Server, title, author string, year int, isbn string) {
	t.Helper()
	code, body := do(t, http.MethodPost, srv.URL+"/books", map[string]any{
		"title":  title,
		"author": author,
		"year":   year,
		"isbn":   isbn,
	})
	if code != http.StatusCreated {
		t.Fatalf("mustCreate: expected 201, got %d body=%v", code, body)
	}
}

// TestUpdateDeleteNotFound covers update, delete, and the 404 path for
// missing ids.
func TestUpdateDeleteNotFound(t *testing.T) {
	srv := newTestServer(t)
	defer srv.Close()

	// Non-existent id -> 404 across GET, PUT, DELETE.
	for _, method := range []string{http.MethodGet, http.MethodPut, http.MethodDelete} {
		var body any
		if method == http.MethodPut {
			body = map[string]any{"title": "X", "author": "Y"}
		}
		if code, _ := do(t, method, srv.URL+"/books/999", body); code != http.StatusNotFound {
			t.Fatalf("%s missing id: expected 404, got %d", method, code)
		}
	}

	// Bad id -> 400.
	if code, _ := do(t, http.MethodGet, srv.URL+"/books/abc", nil); code != http.StatusBadRequest {
		t.Fatalf("get bad id: expected 400, got %d", code)
	}

	// Create, then update, then delete, then confirm gone.
	mustCreate(t, srv, "Original", "Orig Author", 2010, "orig")
	id := firstBookID(t, srv)

	code, body := do(t, http.MethodPut, srv.URL+"/books/"+strconv.Itoa(id), map[string]any{
		"title":  "Updated",
		"author": "Upd Author",
		"year":   2020,
		"isbn":   "upd",
	})
	if code != http.StatusOK || body["title"] != "Updated" {
		t.Fatalf("update: expected 200/Updated, got %d %v", code, body)
	}
	if body["id"].(float64) != float64(id) {
		t.Fatalf("update: id changed from %d to %v", id, body["id"])
	}

	if code, _ := do(t, http.MethodDelete, srv.URL+"/books/"+strconv.Itoa(id), nil); code != http.StatusNoContent {
		t.Fatalf("delete: expected 204, got %d", code)
	}
	if code, _ := do(t, http.MethodGet, srv.URL+"/books/"+strconv.Itoa(id), nil); code != http.StatusNotFound {
		t.Fatalf("get after delete: expected 404, got %d", code)
	}
	// Deleting again -> 404 (not idempotent 204), matching ErrNotFound contract.
	if code, _ := do(t, http.MethodDelete, srv.URL+"/books/"+strconv.Itoa(id), nil); code != http.StatusNotFound {
		t.Fatalf("re-delete: expected 404, got %d", code)
	}
}

// firstBookID returns the id of the first book in the collection.
func firstBookID(t *testing.T, srv *httptest.Server) int {
	t.Helper()
	resp, err := http.Get(srv.URL + "/books")
	if err != nil {
		t.Fatalf("list books: %v", err)
	}
	defer resp.Body.Close()
	var arr []map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&arr); err != nil {
		t.Fatalf("decode list: %v", err)
	}
	if len(arr) == 0 {
		t.Fatal("no books")
	}
	return int(arr[0]["id"].(float64))
}
