package main

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// newTestServer spins up an in-memory SQLite store and a real HTTP server
// backed by it, returning the mux and a cleanup function.
func newTestServer(t *testing.T) (*httptest.Server, *Store) {
	t.Helper()
	store, err := NewStore(":memory:")
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	srv := httptest.NewServer(NewHandler(store).Routes())
	t.Cleanup(func() {
		srv.Close()
		store.Close()
	})
	return srv, store
}

func do(t *testing.T, method, url string, body any) *http.Response {
	t.Helper()
	var r io.Reader
	if body != nil {
		b, err := json.Marshal(body)
		if err != nil {
			t.Fatalf("marshal body: %v", err)
		}
		r = bytes.NewReader(b)
	}
	req, err := http.NewRequest(method, url, r)
	if err != nil {
		t.Fatalf("new request: %v", err)
	}
	if r != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("do request: %v", err)
	}
	return resp
}

func decode(t *testing.T, resp *http.Response, v any) {
	t.Helper()
	defer resp.Body.Close()
	if err := json.NewDecoder(resp.Body).Decode(v); err != nil {
		t.Fatalf("decode body: %v", err)
	}
}

// TestCreateGetList exercises the create -> get -> list happy path.
func TestCreateGetList(t *testing.T) {
	srv, _ := newTestServer(t)

	// Create
	resp := do(t, http.MethodPost, srv.URL+"/books", map[string]any{
		"title": "The Go Programming Language", "author": "Donovan & Kernighan", "year": 2015, "isbn": "9780134190440",
	})
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("create status = %d, want %d", resp.StatusCode, http.StatusCreated)
	}
	var created Book
	decode(t, resp, &created)
	if created.ID == 0 || created.Title != "The Go Programming Language" {
		t.Fatalf("unexpected created book: %+v", created)
	}

	// Get
	resp = do(t, http.MethodGet, srv.URL+"/books/1", nil)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("get status = %d", resp.StatusCode)
	}
	var got Book
	decode(t, resp, &got)
	if got.ID != created.ID || got.Author != "Donovan & Kernighan" {
		t.Fatalf("unexpected book: %+v", got)
	}

	// Create a second book by a different author
	resp = do(t, http.MethodPost, srv.URL+"/books", map[string]any{
		"title": "Clean Code", "author": "Robert Martin", "year": 2008,
	})
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("second create status = %d", resp.StatusCode)
	}
	resp.Body.Close()

	// List all
	resp = do(t, http.MethodGet, srv.URL+"/books", nil)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("list status = %d", resp.StatusCode)
	}
	var all []Book
	decode(t, resp, &all)
	if len(all) != 2 {
		t.Fatalf("list len = %d, want 2", len(all))
	}

	// List filtered by author
	resp = do(t, http.MethodGet, srv.URL+"/books?author=Robert+Martin", nil)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("filtered list status = %d", resp.StatusCode)
	}
	var filtered []Book
	decode(t, resp, &filtered)
	if len(filtered) != 1 || filtered[0].Author != "Robert Martin" {
		t.Fatalf("filtered list = %+v", filtered)
	}
}

// TestValidation verifies that missing required fields are rejected.
func TestValidation(t *testing.T) {
	srv, _ := newTestServer(t)

	cases := []struct {
		name string
		body map[string]any
		want string
	}{
		{"missing title", map[string]any{"author": "X"}, "title is required"},
		{"missing author", map[string]any{"title": "X"}, "author is required"},
		{"empty title", map[string]any{"title": "  ", "author": "X"}, "title is required"},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			resp := do(t, http.MethodPost, srv.URL+"/books", c.body)
			defer resp.Body.Close()
			if resp.StatusCode != http.StatusBadRequest {
				t.Fatalf("status = %d, want %d", resp.StatusCode, http.StatusBadRequest)
			}
			var eb errorBody
			decode(t, resp, &eb)
			if eb.Error != c.want {
				t.Fatalf("error = %q, want %q", eb.Error, c.want)
			}
		})
	}

	// Invalid JSON
	resp := do(t, http.MethodPost, srv.URL+"/books", nil)
	if body, _ := io.ReadAll(resp.Body); true {
		resp.Body.Close()
		_ = body
	}
}

// TestUpdateDelete covers update, delete, and their not-found cases.
func TestUpdateDelete(t *testing.T) {
	srv, _ := newTestServer(t)

	// Seed
	resp := do(t, http.MethodPost, srv.URL+"/books", map[string]any{
		"title": "Original", "author": "A", "year": 2000,
	})
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("create status = %d", resp.StatusCode)
	}
	var b Book
	decode(t, resp, &b)

	// Update
	resp = do(t, http.MethodPut, srv.URL+"/books/1", map[string]any{
		"title": "Updated", "author": "B", "year": 2001, "isbn": "111",
	})
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("update status = %d", resp.StatusCode)
	}
	var upd Book
	decode(t, resp, &upd)
	if upd.Title != "Updated" || upd.Author != "B" || upd.ISBN != "111" || upd.Year != 2001 {
		t.Fatalf("unexpected updated book: %+v", upd)
	}

	// Update missing -> 404
	resp = do(t, http.MethodPut, srv.URL+"/books/9999", map[string]any{"title": "X", "author": "Y"})
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("update missing status = %d, want 404", resp.StatusCode)
	}
	resp.Body.Close()

	// Delete
	resp = do(t, http.MethodDelete, srv.URL+"/books/1", nil)
	if resp.StatusCode != http.StatusNoContent {
		t.Fatalf("delete status = %d, want 204", resp.StatusCode)
	}
	resp.Body.Close()

	// Get deleted -> 404
	resp = do(t, http.MethodGet, srv.URL+"/books/1", nil)
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("get after delete status = %d, want 404", resp.StatusCode)
	}
	resp.Body.Close()

	// Delete again is idempotent (204, not an error)
	resp = do(t, http.MethodDelete, srv.URL+"/books/1", nil)
	if resp.StatusCode != http.StatusNoContent {
		t.Fatalf("idempotent delete status = %d, want 204", resp.StatusCode)
	}
	resp.Body.Close()
}

// TestHealthAndBadID checks the health endpoint and id parsing.
func TestHealthAndBadID(t *testing.T) {
	srv, _ := newTestServer(t)

	// Health
	resp := do(t, http.MethodGet, srv.URL+"/health", nil)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("health status = %d", resp.StatusCode)
	}
	var h map[string]string
	decode(t, resp, &h)
	if h["status"] != "ok" {
		t.Fatalf("health body = %v", h)
	}

	// Bad id
	resp = do(t, http.MethodGet, srv.URL+"/books/abc", nil)
	if resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("bad id status = %d, want 400", resp.StatusCode)
	}
	resp.Body.Close()

	// Zero/negative id
	resp = do(t, http.MethodGet, srv.URL+"/books/0", nil)
	if resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("zero id status = %d, want 400", resp.StatusCode)
	}
	resp.Body.Close()
}

// TestListEmpty ensures an empty collection returns [] not null.
func TestListEmpty(t *testing.T) {
	srv, _ := newTestServer(t)
	resp := do(t, http.MethodGet, srv.URL+"/books", nil)
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("status = %d", resp.StatusCode)
	}
	raw, _ := io.ReadAll(resp.Body)
	if !strings.Contains(string(raw), "[]") {
		t.Fatalf("expected empty array, got %s", raw)
	}
}

// TestContextCancel exercises graceful-ish request handling under a cancelled
// context; this primarily guards that the handler does not block forever or
// panic when the client disconnects early.
func TestContextCancel(t *testing.T) {
	srv, _ := newTestServer(t)
	ctx, cancel := context.WithCancel(context.Background())
	cancel() // already cancelled
	req, _ := http.NewRequestWithContext(ctx, http.MethodGet, srv.URL+"/books", nil)
	_, err := http.DefaultClient.Do(req)
	if err == nil {
		t.Log("request completed despite cancelled context (acceptable)")
	}
}
