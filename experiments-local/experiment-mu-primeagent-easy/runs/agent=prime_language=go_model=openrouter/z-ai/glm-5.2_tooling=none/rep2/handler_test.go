package main

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strconv"
	"testing"
)

// newTestStore creates a fresh SQLite store backed by a temp file.
func newTestStore(t *testing.T) *sqliteStore {
	t.Helper()
	dir := t.TempDir()
	path := filepath.Join(dir, "test.db")
	store, err := NewSQLiteStore(path)
	if err != nil {
		t.Fatalf("new store: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return store
}

// newTestServer wires a handler+store to a test server.
func newTestServer(t *testing.T) (*httptest.Server, *sqliteStore) {
	t.Helper()
	store := newTestStore(t)
	mux := http.NewServeMux()
	NewHandler(store).Register(mux)
	ts := httptest.NewServer(mux)
	t.Cleanup(ts.Close)
	return ts, store
}

// do performs an HTTP request against the test server and returns the
// status code and decoded body.
func do(t *testing.T, ts *httptest.Server, method, path string, body any) (int, []byte) {
	t.Helper()
	var r io.Reader
	if body != nil {
		b, err := json.Marshal(body)
		if err != nil {
			t.Fatalf("marshal body: %v", err)
		}
		r = bytes.NewReader(b)
	}
	req, err := http.NewRequest(method, ts.URL+path, r)
	if err != nil {
		t.Fatalf("new request: %v", err)
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("do request: %v", err)
	}
	defer resp.Body.Close()
	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		t.Fatalf("read body: %v", err)
	}
	return resp.StatusCode, raw
}

// ---------------------------------------------------------------------------
// Store-level tests
// ---------------------------------------------------------------------------

// TestStoreCreateGet verifies that a book can be created and retrieved.
func TestStoreCreateGet(t *testing.T) {
	store := newTestStore(t)

	created, err := store.Create(&Book{
		Title:  "The Go Programming Language",
		Author: "Alan Donovan",
		Year:   2015,
		ISBN:   "9780134190440",
	})
	if err != nil {
		t.Fatalf("create: %v", err)
	}
	if created.ID == 0 {
		t.Fatal("expected non-zero ID after create")
	}

	got, err := store.GetByID(created.ID)
	if err != nil {
		t.Fatalf("get: %v", err)
	}
	if got.Title != "The Go Programming Language" {
		t.Errorf("title = %q, want %q", got.Title, "The Go Programming Language")
	}
	if got.Author != "Alan Donovan" {
		t.Errorf("author = %q, want %q", got.Author, "Alan Donovan")
	}
	if got.Year != 2015 {
		t.Errorf("year = %d, want %d", got.Year, 2015)
	}
	if got.ISBN != "9780134190440" {
		t.Errorf("isbn = %q, want %q", got.ISBN, "9780134190440")
	}
}

// TestStoreGetAllFilter verifies the author filter on GetAll.
func TestStoreGetAllFilter(t *testing.T) {
	store := newTestStore(t)

	books := []Book{
		{Title: "A", Author: "Alice", Year: 2001},
		{Title: "B", Author: "Bob", Year: 2002},
		{Title: "C", Author: "Alice", Year: 2003},
	}
	for _, b := range books {
		if _, err := store.Create(&b); err != nil {
			t.Fatalf("create: %v", err)
		}
	}

	all, err := store.GetAll("")
	if err != nil {
		t.Fatalf("get all: %v", err)
	}
	if len(all) != 3 {
		t.Errorf("len(all) = %d, want 3", len(all))
	}

	alice, err := store.GetAll("Alice")
	if err != nil {
		t.Fatalf("get alice: %v", err)
	}
	if len(alice) != 2 {
		t.Errorf("len(alice) = %d, want 2", len(alice))
	}
}

// TestStoreUpdateDelete verifies updating and deleting a book.
func TestStoreUpdateDelete(t *testing.T) {
	store := newTestStore(t)

	created, err := store.Create(&Book{Title: "Old", Author: "Auth", Year: 2000})
	if err != nil {
		t.Fatalf("create: %v", err)
	}

	updated, err := store.Update(created.ID, &Book{Title: "New", Author: "Auth2", Year: 2001, ISBN: "123"})
	if err != nil {
		t.Fatalf("update: %v", err)
	}
	if updated.Title != "New" || updated.Author != "Auth2" || updated.ISBN != "123" {
		t.Errorf("updated = %+v", updated)
	}

	got, err := store.GetByID(created.ID)
	if err != nil {
		t.Fatalf("get after update: %v", err)
	}
	if got.Title != "New" {
		t.Errorf("title = %q, want %q", got.Title, "New")
	}

	if err := store.Delete(created.ID); err != nil {
		t.Fatalf("delete: %v", err)
	}

	if _, err := store.GetByID(created.ID); err == nil {
		t.Fatal("expected error after delete, got nil")
	}
}

// ---------------------------------------------------------------------------
// HTTP handler integration tests
// ---------------------------------------------------------------------------

// TestHTTPHealth verifies the health check endpoint.
func TestHTTPHealth(t *testing.T) {
	ts, _ := newTestServer(t)
	status, body := do(t, ts, http.MethodGet, "/health", nil)
	if status != http.StatusOK {
		t.Errorf("status = %d, want %d", status, http.StatusOK)
	}
	var resp map[string]string
	if err := json.Unmarshal(body, &resp); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if resp["status"] != "ok" {
		t.Errorf("status = %q, want %q", resp["status"], "ok")
	}
}

// TestHTTPCreateAndGet verifies creating a book via the API and
// retrieving it by ID.
func TestHTTPCreateAndGet(t *testing.T) {
	ts, _ := newTestServer(t)

	// Create
	status, body := do(t, ts, http.MethodPost, "/books", bookRequest{
		Title:  "Clean Code",
		Author: "Robert Martin",
		Year:   2008,
		ISBN:   "9780132350884",
	})
	if status != http.StatusCreated {
		t.Fatalf("create status = %d, want %d; body=%s", status, http.StatusCreated, body)
	}
	var created Book
	if err := json.Unmarshal(body, &created); err != nil {
		t.Fatalf("unmarshal created: %v", err)
	}
	if created.ID == 0 {
		t.Fatal("expected non-zero ID")
	}
	if created.Title != "Clean Code" {
		t.Errorf("title = %q", created.Title)
	}

	// Get by ID
	status, body = do(t, ts, http.MethodGet, "/books/1", nil)
	if status != http.StatusOK {
		t.Fatalf("get status = %d, want %d; body=%s", status, http.StatusOK, body)
	}
	var got Book
	if err := json.Unmarshal(body, &got); err != nil {
		t.Fatalf("unmarshal got: %v", err)
	}
	if got.Title != "Clean Code" || got.Author != "Robert Martin" {
		t.Errorf("got = %+v", got)
	}
}

// TestHTTPValidation verifies that missing title/author returns 400.
func TestHTTPValidation(t *testing.T) {
	ts, _ := newTestServer(t)

	cases := []struct {
		name string
		body bookRequest
	}{
		{"missing title", bookRequest{Author: "Auth", Year: 2020}},
		{"missing author", bookRequest{Title: "Title", Year: 2020}},
		{"missing both", bookRequest{Year: 2020}},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			status, body := do(t, ts, http.MethodPost, "/books", tc.body)
			if status != http.StatusBadRequest {
				t.Errorf("status = %d, want %d; body=%s", status, http.StatusBadRequest, body)
			}
		})
	}
}

// TestHTTPListWithAuthorFilter verifies listing and the author query filter.
func TestHTTPListWithAuthorFilter(t *testing.T) {
	ts, _ := newTestServer(t)

	// Seed two books by different authors.
	for _, b := range []bookRequest{
		{Title: "Book1", Author: "Alice", Year: 2010},
		{Title: "Book2", Author: "Bob", Year: 2011},
		{Title: "Book3", Author: "Alice", Year: 2012},
	} {
		if status, _ := do(t, ts, http.MethodPost, "/books", b); status != http.StatusCreated {
			t.Fatalf("seed create status = %d", status)
		}
	}

	// List all
	status, body := do(t, ts, http.MethodGet, "/books", nil)
	if status != http.StatusOK {
		t.Fatalf("list status = %d, want %d", status, http.StatusOK)
	}
	var all []Book
	if err := json.Unmarshal(body, &all); err != nil {
		t.Fatalf("unmarshal all: %v", err)
	}
	if len(all) != 3 {
		t.Errorf("len(all) = %d, want 3", len(all))
	}

	// Filter by author=Alice
	status, body = do(t, ts, http.MethodGet, "/books?author=Alice", nil)
	if status != http.StatusOK {
		t.Fatalf("list filtered status = %d, want %d", status, http.StatusOK)
	}
	var filtered []Book
	if err := json.Unmarshal(body, &filtered); err != nil {
		t.Fatalf("unmarshal filtered: %v", err)
	}
	if len(filtered) != 2 {
		t.Errorf("len(filtered) = %d, want 2", len(filtered))
	}
	for _, b := range filtered {
		if b.Author != "Alice" {
			t.Errorf("author = %q, want Alice", b.Author)
		}
	}
}

// TestHTTPUpdate verifies updating a book via PUT.
func TestHTTPUpdate(t *testing.T) {
	ts, _ := newTestServer(t)

	// Create
	status, body := do(t, ts, http.MethodPost, "/books", bookRequest{
		Title: "Original", Author: "Auth", Year: 2000,
	})
	if status != http.StatusCreated {
		t.Fatalf("create status = %d", status)
	}
	var created Book
	if err := json.Unmarshal(body, &created); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}

	// Update
	status, body = do(t, ts, http.MethodPut, "/books/"+strconv.FormatInt(created.ID, 10), bookRequest{
		Title: "Updated", Author: "NewAuth", Year: 2001, ISBN: "999",
	})
	if status != http.StatusOK {
		t.Fatalf("update status = %d, want %d; body=%s", status, http.StatusOK, body)
	}
	var updated Book
	if err := json.Unmarshal(body, &updated); err != nil {
		t.Fatalf("unmarshal updated: %v", err)
	}
	if updated.Title != "Updated" || updated.Author != "NewAuth" || updated.ISBN != "999" {
		t.Errorf("updated = %+v", updated)
	}
}

// TestHTTPDelete verifies deleting a book and subsequent 404.
func TestHTTPDelete(t *testing.T) {
	ts, _ := newTestServer(t)

	// Create
	status, body := do(t, ts, http.MethodPost, "/books", bookRequest{
		Title: "ToDelete", Author: "Auth", Year: 2000,
	})
	if status != http.StatusCreated {
		t.Fatalf("create status = %d", status)
	}
	var created Book
	if err := json.Unmarshal(body, &created); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}

	// Delete
	status, _ = do(t, ts, http.MethodDelete, "/books/"+strconv.FormatInt(created.ID, 10), nil)
	if status != http.StatusNoContent {
		t.Errorf("delete status = %d, want %d", status, http.StatusNoContent)
	}

	// Get deleted -> 404
	status, _ = do(t, ts, http.MethodGet, "/books/"+strconv.FormatInt(created.ID, 10), nil)
	if status != http.StatusNotFound {
		t.Errorf("get after delete status = %d, want %d", status, http.StatusNotFound)
	}
}

// TestHTTPNotFound verifies that a missing book returns 404.
func TestHTTPNotFound(t *testing.T) {
	ts, _ := newTestServer(t)
	status, _ := do(t, ts, http.MethodGet, "/books/999", nil)
	if status != http.StatusNotFound {
		t.Errorf("status = %d, want %d", status, http.StatusNotFound)
	}
}

// TestHTTPInvalidJSON verifies that a malformed body returns 400.
func TestHTTPInvalidJSON(t *testing.T) {
	ts, _ := newTestServer(t)

	req, err := http.NewRequest(http.MethodPost, ts.URL+"/books", bytes.NewReader([]byte("{bad json")))
	if err != nil {
		t.Fatal(err)
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("status = %d, want %d", resp.StatusCode, http.StatusBadRequest)
	}
}
