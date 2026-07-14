package server

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"

	"bookapi/internal/book"
)

func newTestServer(t *testing.T) (*httptest.Server, *book.Store) {
	t.Helper()
	dir := t.TempDir()
	store, err := book.NewStore(context.Background(), filepath.Join(dir, "test.db"))
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	srv := httptest.NewServer(New(store))
	t.Cleanup(srv.Close)
	return srv, store
}

func do(t *testing.T, method, url string, body any) *http.Response {
	t.Helper()
	var r bytes.Reader
	if body != nil {
		b, err := json.Marshal(body)
		if err != nil {
			t.Fatalf("marshal: %v", err)
		}
		r = *bytes.NewReader(b)
	}
	req, err := http.NewRequest(method, url, &r)
	if err != nil {
		t.Fatalf("NewRequest: %v", err)
	}
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("Do: %v", err)
	}
	return resp
}

func TestHealth(t *testing.T) {
	srv, _ := newTestServer(t)
	resp := do(t, "GET", srv.URL+"/health", nil)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("status = %d, want 200", resp.StatusCode)
	}
}

func TestCreateGetListDelete(t *testing.T) {
	srv, _ := newTestServer(t)
	base := srv.URL + "/books"

	// Create
	resp := do(t, "POST", base, map[string]any{
		"title": "Dune", "author": "Herbert", "year": 1965, "isbn": "9780441172719",
	})
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("create status = %d", resp.StatusCode)
	}
	var created book.Book
	if err := json.NewDecoder(resp.Body).Decode(&created); err != nil {
		t.Fatalf("decode: %v", err)
	}
	resp.Body.Close()
	if created.ID == 0 {
		t.Fatal("expected non-zero id")
	}

	// Get single
	resp = do(t, "GET", base+"/"+itoa(created.ID), nil)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("get status = %d", resp.StatusCode)
	}
	resp.Body.Close()

	// Create second with different author for filter test
	resp = do(t, "POST", base, map[string]any{"title": "T2", "author": "Other"})
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("create2 status = %d", resp.StatusCode)
	}
	resp.Body.Close()

	// List all
	resp = do(t, "GET", base, nil)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("list status = %d", resp.StatusCode)
	}
	var list []book.Book
	if err := json.NewDecoder(resp.Body).Decode(&list); err != nil {
		t.Fatalf("decode list: %v", err)
	}
	resp.Body.Close()
	if len(list) != 2 {
		t.Fatalf("expected 2 books, got %d", len(list))
	}

	// List filtered
	resp = do(t, "GET", base+"?author=Herbert", nil)
	var filtered []book.Book
	json.NewDecoder(resp.Body).Decode(&filtered)
	resp.Body.Close()
	if len(filtered) != 1 || filtered[0].Title != "Dune" {
		t.Fatalf("filter result = %+v", filtered)
	}

	// Update
	resp = do(t, "PUT", base+"/"+itoa(created.ID), map[string]any{
		"title": "Dune Updated", "author": "Herbert", "year": 1966,
	})
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("update status = %d", resp.StatusCode)
	}
	var updated book.Book
	json.NewDecoder(resp.Body).Decode(&updated)
	resp.Body.Close()
	if updated.Title != "Dune Updated" {
		t.Fatalf("updated title = %q", updated.Title)
	}

	// Delete
	resp = do(t, "DELETE", base+"/"+itoa(created.ID), nil)
	if resp.StatusCode != http.StatusNoContent {
		t.Fatalf("delete status = %d", resp.StatusCode)
	}
	resp.Body.Close()

	// Get after delete -> 404
	resp = do(t, "GET", base+"/"+itoa(created.ID), nil)
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("get-after-delete status = %d", resp.StatusCode)
	}
	resp.Body.Close()
}

func TestValidationErrors(t *testing.T) {
	srv, _ := newTestServer(t)
	base := srv.URL + "/books"

	// Missing author -> 400
	resp := do(t, "POST", base, map[string]any{"title": "Only Title"})
	if resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("missing-author status = %d, want 400", resp.StatusCode)
	}
	resp.Body.Close()

	// Missing title -> 400
	resp = do(t, "POST", base, map[string]any{"author": "Only Author"})
	if resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("missing-title status = %d, want 400", resp.StatusCode)
	}
	resp.Body.Close()

	// Invalid JSON -> 400
	req, _ := http.NewRequest("POST", base, strings.NewReader("{not json"))
	req.Header.Set("Content-Type", "application/json")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("Do: %v", err)
	}
	if resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("bad-json status = %d, want 400", resp.StatusCode)
	}
	resp.Body.Close()

	// Invalid id -> 400
	resp = do(t, "GET", base+"/abc", nil)
	if resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("bad-id status = %d, want 400", resp.StatusCode)
	}
	resp.Body.Close()

	// Unknown field -> 400 (DisallowUnknownFields)
	resp = do(t, "POST", base, map[string]any{"title": "T", "author": "A", "publisher": "X"})
	if resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("unknown-field status = %d, want 400", resp.StatusCode)
	}
	resp.Body.Close()
}

func TestUpdateNotFound(t *testing.T) {
	srv, _ := newTestServer(t)
	base := srv.URL + "/books"
	resp := do(t, "PUT", base+"/9999", map[string]any{"title": "T", "author": "A"})
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("status = %d, want 404", resp.StatusCode)
	}
	resp.Body.Close()
}

func itoa(n int64) string {
	const digits = "0123456789"
	if n == 0 {
		return "0"
	}
	var buf [20]byte
	i := len(buf)
	for n > 0 {
		i--
		buf[i] = digits[n%10]
		n /= 10
	}
	return string(buf[i:])
}
