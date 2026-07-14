package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
)

func newTestServer(t *testing.T) (*Server, func()) {
	t.Helper()
	f, err := os.CreateTemp("", "books_test_*.db")
	if err != nil {
		t.Fatal(err)
	}
	path := f.Name()
	f.Close()

	store, err := NewBookStore(path)
	if err != nil {
		os.Remove(path)
		t.Fatal(err)
	}

	srv := NewServer(store)
	cleanup := func() {
		store.Close()
		os.Remove(path)
	}
	return srv, cleanup
}

func decodeBody(t *testing.T, body *bytes.Buffer) map[string]interface{} {
	t.Helper()
	var m map[string]interface{}
	if err := json.Unmarshal(body.Bytes(), &m); err != nil {
		t.Fatalf("decode json: %v", err)
	}
	return m
}

func TestHealthEndpoint(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()

	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	w := httptest.NewRecorder()
	srv.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
	m := decodeBody(t, w.Body)
	if m["status"] != "ok" {
		t.Fatalf("expected status ok, got %v", m["status"])
	}
}

func TestCreateAndGetBook(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()

	year := 2024
	input := BookInput{Title: "The Go Programming Language", Author: "Donovan & Kernighan", Year: &year, ISBN: "978-0134190440"}
	body, _ := json.Marshal(input)

	// Create
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	srv.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Fatalf("expected 201, got %d; body: %s", w.Code, w.Body.String())
	}

	created := decodeBody(t, w.Body)
	if created["title"] != input.Title {
		t.Fatalf("expected title %q, got %v", input.Title, created["title"])
	}
	id := created["id"]

	// Get
	req = httptest.NewRequest(http.MethodGet, "/books/"+jsonNumberStr(id), nil)
	w = httptest.NewRecorder()
	srv.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
	got := decodeBody(t, w.Body)
	if got["title"] != input.Title {
		t.Fatalf("expected title %q, got %v", input.Title, got["title"])
	}
}

func TestCreateBookValidation(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()

	// Missing title
	input := BookInput{Author: "Author Only"}
	body, _ := json.Marshal(input)
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	srv.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 for missing title, got %d", w.Code)
	}

	// Missing author
	input = BookInput{Title: "Title Only"}
	body, _ = json.Marshal(input)
	req = httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w = httptest.NewRecorder()
	srv.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 for missing author, got %d", w.Code)
	}
}

func TestListBooksWithFilter(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()

	// Create two books
	for _, input := range []BookInput{
		{Title: "Book A", Author: "Alice"},
		{Title: "Book B", Author: "Bob"},
	} {
		body, _ := json.Marshal(input)
		req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		srv.ServeHTTP(w, req)
		if w.Code != http.StatusCreated {
			t.Fatalf("create book failed: %d", w.Code)
		}
	}

	// List all
	req := httptest.NewRequest(http.MethodGet, "/books", nil)
	w := httptest.NewRecorder()
	srv.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
	var all []interface{}
	json.Unmarshal(w.Body.Bytes(), &all)
	if len(all) != 2 {
		t.Fatalf("expected 2 books, got %d", len(all))
	}

	// Filter by author
	req = httptest.NewRequest(http.MethodGet, "/books?author=Alice", nil)
	w = httptest.NewRecorder()
	srv.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
	var filtered []interface{}
	json.Unmarshal(w.Body.Bytes(), &filtered)
	if len(filtered) != 1 {
		t.Fatalf("expected 1 book for Alice, got %d", len(filtered))
	}
}

func TestUpdateBook(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()

	// Create
	input := BookInput{Title: "Original", Author: "Author"}
	body, _ := json.Marshal(input)
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	srv.ServeHTTP(w, req)
	created := decodeBody(t, w.Body)
	id := jsonNumberStr(created["id"])

	// Update
	updated := BookInput{Title: "Updated", Author: "New Author"}
	body, _ = json.Marshal(updated)
	req = httptest.NewRequest(http.MethodPut, "/books/"+id, bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w = httptest.NewRecorder()
	srv.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d; body: %s", w.Code, w.Body.String())
	}
	result := decodeBody(t, w.Body)
	if result["title"] != "Updated" {
		t.Fatalf("expected title Updated, got %v", result["title"])
	}
}

func TestDeleteBook(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()

	// Create
	input := BookInput{Title: "To Delete", Author: "Author"}
	body, _ := json.Marshal(input)
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	srv.ServeHTTP(w, req)
	created := decodeBody(t, w.Body)
	id := jsonNumberStr(created["id"])

	// Delete
	req = httptest.NewRequest(http.MethodDelete, "/books/"+id, nil)
	w = httptest.NewRecorder()
	srv.ServeHTTP(w, req)
	if w.Code != http.StatusNoContent {
		t.Fatalf("expected 204, got %d", w.Code)
	}

	// Verify gone
	req = httptest.NewRequest(http.MethodGet, "/books/"+id, nil)
	w = httptest.NewRecorder()
	srv.ServeHTTP(w, req)
	if w.Code != http.StatusNotFound {
		t.Fatalf("expected 404 after delete, got %d", w.Code)
	}
}

func TestGetBookNotFound(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()

	req := httptest.NewRequest(http.MethodGet, "/books/9999", nil)
	w := httptest.NewRecorder()
	srv.ServeHTTP(w, req)
	if w.Code != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", w.Code)
	}
}

// jsonNumberStr converts a JSON-decoded number (float64) to a string without decimals.
func jsonNumberStr(v interface{}) string {
	switch n := v.(type) {
	case float64:
		return formatInt(int64(n))
	}
	return ""
}

func formatInt(n int64) string {
	if n == 0 {
		return "0"
	}
	neg := false
	if n < 0 {
		neg = true
		n = -n
	}
	var buf [20]byte
	i := len(buf)
	for n > 0 {
		i--
		buf[i] = byte('0' + n%10)
		n /= 10
	}
	if neg {
		i--
		buf[i] = '-'
	}
	return string(buf[i:])
}
