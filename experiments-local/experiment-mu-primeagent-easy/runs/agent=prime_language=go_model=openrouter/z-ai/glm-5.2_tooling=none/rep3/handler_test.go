package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// newTestServer returns a Server backed by an in-memory SQLite database.
func newTestServer(t *testing.T) (*Server, func()) {
	t.Helper()
	storage, err := NewStorage(":memory:")
	if err != nil {
		t.Fatalf("create storage: %v", err)
	}
	srv := NewServer(storage)
	cleanup := func() { storage.Close() }
	return srv, cleanup
}

// --- Test 1: create + retrieve a book ---

func TestCreateAndGetBook(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()

	body := `{"title":"The Go Programming Language","author":"Alan Donovan","year":2015,"isbn":"9780134190440"}`
	resp := doRequest(t, srv, http.MethodPost, "/books", body)
	if resp.Code != http.StatusCreated {
		t.Fatalf("expected 201, got %d: %s", resp.Code, resp.Body.String())
	}

	var created Book
	if err := json.Unmarshal(resp.Body.Bytes(), &created); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if created.ID == 0 {
		t.Fatal("expected non-zero ID")
	}
	if created.Title != "The Go Programming Language" {
		t.Errorf("title: got %q", created.Title)
	}

	// GET the book back
	resp = doRequest(t, srv, http.MethodGet, "/books/1", "")
	if resp.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.Code)
	}

	var fetched Book
	if err := json.Unmarshal(resp.Body.Bytes(), &fetched); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if fetched.Title != created.Title {
		t.Errorf("fetched title: got %q, want %q", fetched.Title, created.Title)
	}
}

// --- Test 2: list books with author filter ---

func TestListBooksWithAuthorFilter(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()

	// seed two books by different authors
	books := []Book{
		{Title: "Book A", Author: "Alice", Year: 2020, ISBN: "111"},
		{Title: "Book B", Author: "Bob", Year: 2021, ISBN: "222"},
		{Title: "Book C", Author: "Alice", Year: 2022, ISBN: "333"},
	}
	for _, b := range books {
		payload, _ := json.Marshal(b)
		resp := doRequest(t, srv, http.MethodPost, "/books", string(payload))
		if resp.Code != http.StatusCreated {
			t.Fatalf("seed book: expected 201, got %d", resp.Code)
		}
	}

	// list all
	resp := doRequest(t, srv, http.MethodGet, "/books", "")
	if resp.Code != http.StatusOK {
		t.Fatalf("list all: expected 200, got %d", resp.Code)
	}
	var all []Book
	if err := json.Unmarshal(resp.Body.Bytes(), &all); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if len(all) != 3 {
		t.Errorf("expected 3 books, got %d", len(all))
	}

	// list filtered by author
	resp = doRequest(t, srv, http.MethodGet, "/books?author=Alice", "")
	if resp.Code != http.StatusOK {
		t.Fatalf("list filtered: expected 200, got %d", resp.Code)
	}
	var filtered []Book
	if err := json.Unmarshal(resp.Body.Bytes(), &filtered); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if len(filtered) != 2 {
		t.Errorf("expected 2 books by Alice, got %d", len(filtered))
	}
	for _, b := range filtered {
		if b.Author != "Alice" {
			t.Errorf("unexpected author %q", b.Author)
		}
	}
}

// --- Test 3: update and delete ---

func TestUpdateAndDeleteBook(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()

	// create
	body := `{"title":"Original","author":"Author","year":2000,"isbn":"abc"}`
	resp := doRequest(t, srv, http.MethodPost, "/books", body)
	if resp.Code != http.StatusCreated {
		t.Fatalf("create: expected 201, got %d", resp.Code)
	}

	// update
	updateBody := `{"title":"Updated","author":"NewAuthor","year":2023,"isbn":"xyz"}`
	resp = doRequest(t, srv, http.MethodPut, "/books/1", updateBody)
	if resp.Code != http.StatusOK {
		t.Fatalf("update: expected 200, got %d: %s", resp.Code, resp.Body.String())
	}
	var updated Book
	if err := json.Unmarshal(resp.Body.Bytes(), &updated); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if updated.Title != "Updated" || updated.Author != "NewAuthor" || updated.Year != 2023 {
		t.Errorf("unexpected book: %+v", updated)
	}

	// delete
	resp = doRequest(t, srv, http.MethodDelete, "/books/1", "")
	if resp.Code != http.StatusNoContent {
		t.Fatalf("delete: expected 204, got %d", resp.Code)
	}

	// verify gone
	resp = doRequest(t, srv, http.MethodGet, "/books/1", "")
	if resp.Code != http.StatusNotFound {
		t.Errorf("get after delete: expected 404, got %d", resp.Code)
	}
}

// --- Test 4: validation ---

func TestValidationMissingTitleAndAuthor(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()

	// missing title
	resp := doRequest(t, srv, http.MethodPost, "/books", `{"author":"Author"}`)
	if resp.Code != http.StatusBadRequest {
		t.Fatalf("missing title: expected 400, got %d: %s", resp.Code, resp.Body.String())
	}
	if !strings.Contains(resp.Body.String(), "title is required") {
		t.Errorf("expected 'title is required' in body: %s", resp.Body.String())
	}

	// missing author
	resp = doRequest(t, srv, http.MethodPost, "/books", `{"title":"Title"}`)
	if resp.Code != http.StatusBadRequest {
		t.Fatalf("missing author: expected 400, got %d", resp.Code)
	}
	if !strings.Contains(resp.Body.String(), "author is required") {
		t.Errorf("expected 'author is required' in body: %s", resp.Body.String())
	}

	// invalid JSON
	resp = doRequest(t, srv, http.MethodPost, "/books", `{not json`)
	if resp.Code != http.StatusBadRequest {
		t.Fatalf("invalid json: expected 400, got %d", resp.Code)
	}
}

// --- Test 5: health check ---

func TestHealthCheck(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()

	resp := doRequest(t, srv, http.MethodGet, "/health", "")
	if resp.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.Code)
	}
	if ct := resp.Header().Get("Content-Type"); !strings.HasPrefix(ct, "application/json") {
		t.Errorf("expected json content type, got %q", ct)
	}
	var result map[string]string
	if err := json.Unmarshal(resp.Body.Bytes(), &result); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if result["status"] != "ok" {
		t.Errorf("expected status ok, got %q", result["status"])
	}
}

// --- Test 6: not found returns 404 ---

func TestGetBookNotFound(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()

	resp := doRequest(t, srv, http.MethodGet, "/books/999", "")
	if resp.Code != http.StatusNotFound {
		t.Errorf("expected 404, got %d", resp.Code)
	}

	// non-numeric id should also 404
	resp = doRequest(t, srv, http.MethodGet, "/books/abc", "")
	if resp.Code != http.StatusNotFound {
		t.Errorf("expected 404 for non-numeric id, got %d", resp.Code)
	}
}

// --- helpers ---

func doRequest(t *testing.T, srv *Server, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	var buf *bytes.Buffer
	if body != "" {
		buf = bytes.NewBufferString(body)
	}
	var r *http.Request
	var err error
	if buf != nil {
		r, err = http.NewRequest(method, path, buf)
	} else {
		r, err = http.NewRequest(method, path, nil)
	}
	if err != nil {
		t.Fatalf("new request: %v", err)
	}

	w := httptest.NewRecorder()
	srv.ServeHTTP(w, r)
	return w
}
