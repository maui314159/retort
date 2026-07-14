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

// newTestServer spins up an httptest server backed by a fresh SQLite file.
// Each test gets an isolated database so they can run in parallel and so a
// failure in one cannot affect another.
func newTestServer(t *testing.T) *httptest.Server {
	t.Helper()
	dsn := filepath.Join(t.TempDir(), "books.db")
	store, err := NewStore(dsn)
	if err != nil {
		t.Fatalf("init store: %v", err)
	}
	t.Cleanup(func() { _ = store.Close() })

	ts := httptest.NewServer(newAPI(store).routes())
	t.Cleanup(ts.Close)
	return ts
}

// do is a tiny helper that issues a request and returns status + body.
func do(t *testing.T, method, url, body string) (int, []byte) {
	t.Helper()
	var r io.Reader
	if body != "" {
		r = bytes.NewReader([]byte(body))
	}
	req, err := http.NewRequest(method, url, r)
	if err != nil {
		t.Fatalf("new request: %v", err)
	}
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("do request: %v", err)
	}
	defer resp.Body.Close()
	out, err := io.ReadAll(resp.Body)
	if err != nil {
		t.Fatalf("read body: %v", err)
	}
	return resp.StatusCode, out
}

func TestHealth(t *testing.T) {
	ts := newTestServer(t)
	status, body := do(t, "GET", ts.URL+"/health", "")
	if status != http.StatusOK {
		t.Fatalf("status: got %d, want 200, body=%s", status, body)
	}
	var got map[string]string
	if err := json.Unmarshal(body, &got); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if got["status"] != "ok" {
		t.Errorf("status field: got %q, want %q", got["status"], "ok")
	}
}

func TestCreateAndGetBook(t *testing.T) {
	ts := newTestServer(t)

	// Create
	status, body := do(t, "POST", ts.URL+"/books",
		`{"title":"The Go Programming Language","author":"Alan A. A. Donovan","year":2015,"isbn":"978-0134190440"}`)
	if status != http.StatusCreated {
		t.Fatalf("create: status %d body %s", status, body)
	}
	var created Book
	if err := json.Unmarshal(body, &created); err != nil {
		t.Fatalf("decode created: %v", err)
	}
	if created.ID == 0 {
		t.Errorf("expected non-zero id, got 0")
	}
	if created.Title != "The Go Programming Language" {
		t.Errorf("title: got %q", created.Title)
	}
	if created.CreatedAt.IsZero() {
		t.Errorf("expected CreatedAt to be populated")
	}

	// Get
	status, body = do(t, "GET", ts.URL+"/books/"+strconv.FormatInt(created.ID, 10), "")
	if status != http.StatusOK {
		t.Fatalf("get: status %d body %s", status, body)
	}
	var got Book
	if err := json.Unmarshal(body, &got); err != nil {
		t.Fatalf("decode got: %v", err)
	}
	if got.ID != created.ID || got.Title != created.Title || got.Author != created.Author {
		t.Errorf("get mismatch: got %+v want %+v", got, created)
	}
}

func TestListAndFilterBooks(t *testing.T) {
	ts := newTestServer(t)
	seed := []string{
		`{"title":"Book A","author":"Alice","year":2000,"isbn":"a"}`,
		`{"title":"Book B","author":"Bob","year":2001,"isbn":"b"}`,
		`{"title":"Book C","author":"Alice","year":2002,"isbn":"c"}`,
	}
	for _, s := range seed {
		status, body := do(t, "POST", ts.URL+"/books", s)
		if status != http.StatusCreated {
			t.Fatalf("seed: status %d body %s", status, body)
		}
	}

	// List all
	status, body := do(t, "GET", ts.URL+"/books", "")
	if status != http.StatusOK {
		t.Fatalf("list: status %d", status)
	}
	var all []Book
	if err := json.Unmarshal(body, &all); err != nil {
		t.Fatalf("decode list: %v", err)
	}
	if len(all) != 3 {
		t.Errorf("list all: got %d, want 3", len(all))
	}

	// Filter by author
	status, body = do(t, "GET", ts.URL+"/books?author=Alice", "")
	if status != http.StatusOK {
		t.Fatalf("filter: status %d", status)
	}
	var filtered []Book
	if err := json.Unmarshal(body, &filtered); err != nil {
		t.Fatalf("decode filtered: %v", err)
	}
	if len(filtered) != 2 {
		t.Errorf("filter: got %d, want 2", len(filtered))
	}
	for _, b := range filtered {
		if b.Author != "Alice" {
			t.Errorf("filter leaked non-Alice: %+v", b)
		}
	}

	// Empty filter result still returns []
	status, body = do(t, "GET", ts.URL+"/books?author=Nobody", "")
	if status != http.StatusOK {
		t.Fatalf("empty filter: status %d", status)
	}
	var empty []Book
	if err := json.Unmarshal(body, &empty); err != nil {
		t.Fatalf("decode empty: %v", err)
	}
	if len(empty) != 0 {
		t.Errorf("empty filter: got %d, want 0", len(empty))
	}
}

func TestUpdateBook(t *testing.T) {
	ts := newTestServer(t)
	status, body := do(t, "POST", ts.URL+"/books",
		`{"title":"Old","author":"A","year":2000,"isbn":"old"}`)
	if status != http.StatusCreated {
		t.Fatalf("create: status %d", status)
	}
	var created Book
	if err := json.Unmarshal(body, &created); err != nil {
		t.Fatalf("decode: %v", err)
	}

	status, body = do(t, "PUT", ts.URL+"/books/"+strconv.FormatInt(created.ID, 10),
		`{"title":"New","author":"B","year":2020,"isbn":"new"}`)
	if status != http.StatusOK {
		t.Fatalf("update: status %d body %s", status, body)
	}
	var got Book
	if err := json.Unmarshal(body, &got); err != nil {
		t.Fatalf("decode updated: %v", err)
	}
	if got.Title != "New" || got.Author != "B" || got.Year != 2020 || got.ISBN != "new" {
		t.Errorf("update: got %+v", got)
	}
	if !got.UpdatedAt.After(created.UpdatedAt) && !got.UpdatedAt.Equal(created.UpdatedAt) {
		t.Errorf("expected updated_at to be >= created.UpdatedAt, got %v vs %v", got.UpdatedAt, created.UpdatedAt)
	}
}

func TestDeleteBook(t *testing.T) {
	ts := newTestServer(t)
	status, body := do(t, "POST", ts.URL+"/books",
		`{"title":"To Delete","author":"X","year":2000,"isbn":"d"}`)
	if status != http.StatusCreated {
		t.Fatalf("create: status %d", status)
	}
	var created Book
	_ = json.Unmarshal(body, &created)

	status, _ = do(t, "DELETE", ts.URL+"/books/"+strconv.FormatInt(created.ID, 10), "")
	if status != http.StatusNoContent {
		t.Fatalf("delete: status %d", status)
	}

	status, _ = do(t, "GET", ts.URL+"/books/"+strconv.FormatInt(created.ID, 10), "")
	if status != http.StatusNotFound {
		t.Errorf("expected 404 after delete, got %d", status)
	}
}

func TestValidation(t *testing.T) {
	ts := newTestServer(t)
	cases := []struct {
		name, body string
		want       int
	}{
		{"empty body", `{}`, http.StatusBadRequest},
		{"missing title", `{"author":"A"}`, http.StatusBadRequest},
		{"missing author", `{"title":"T"}`, http.StatusBadRequest},
		{"empty title", `{"title":"","author":"A"}`, http.StatusBadRequest},
		{"whitespace title", `{"title":"   ","author":"A"}`, http.StatusBadRequest},
		{"whitespace author", `{"title":"T","author":"\t"}`, http.StatusBadRequest},
		{"invalid json", `{not json`, http.StatusBadRequest},
		{"negative year", `{"title":"T","author":"A","year":-5}`, http.StatusBadRequest},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			status, body := do(t, "POST", ts.URL+"/books", tc.body)
			if status != tc.want {
				t.Errorf("got %d, want %d, body=%s", status, tc.want, body)
			}
		})
	}
}

func TestNotFoundAndBadID(t *testing.T) {
	ts := newTestServer(t)

	// Bad ID format
	status, _ := do(t, "GET", ts.URL+"/books/abc", "")
	if status != http.StatusBadRequest {
		t.Errorf("bad id (GET): got %d, want 400", status)
	}
	status, _ = do(t, "PUT", ts.URL+"/books/notanumber", `{"title":"T","author":"A"}`)
	if status != http.StatusBadRequest {
		t.Errorf("bad id (PUT): got %d, want 400", status)
	}
	status, _ = do(t, "DELETE", ts.URL+"/books/-7", "")
	if status != http.StatusBadRequest {
		t.Errorf("negative id (DELETE): got %d, want 400", status)
	}

	// Non-existent ids
	status, _ = do(t, "GET", ts.URL+"/books/9999", "")
	if status != http.StatusNotFound {
		t.Errorf("missing (GET): got %d, want 404", status)
	}
	status, _ = do(t, "DELETE", ts.URL+"/books/9999", "")
	if status != http.StatusNotFound {
		t.Errorf("missing (DELETE): got %d, want 404", status)
	}
	status, _ = do(t, "PUT", ts.URL+"/books/9999",
		`{"title":"T","author":"A","year":2020,"isbn":""}`)
	if status != http.StatusNotFound {
		t.Errorf("missing (PUT): got %d, want 404", status)
	}
}

func TestMethodNotAllowed(t *testing.T) {
	ts := newTestServer(t)
	// The mux returns 405 automatically for method/path mismatches.
	status, _ := do(t, "PATCH", ts.URL+"/books/1", `{"title":"T"}`)
	if status != http.StatusMethodNotAllowed {
		t.Errorf("PATCH: got %d, want 405", status)
	}
}
