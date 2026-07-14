package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
)

// newTestServer spins up an in-memory-backed SQLite file in a temp dir and
// returns a ready-to-use httptest server plus a cleanup function.
func newTestServer(t *testing.T) (*httptest.Server, *sql.DB) {
	t.Helper()
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "test.db")
	if err := os.WriteFile(dbPath, nil, 0o644); err != nil {
		t.Fatalf("seed db: %v", err)
	}
	db, err := openDB(dbPath)
	if err != nil {
		t.Fatalf("openDB: %v", err)
	}

	mux := http.NewServeMux()
	newAPIServer(db).registerRoutes(mux)
	srv := httptest.NewServer(mux)
	t.Cleanup(func() {
		srv.Close()
		db.Close()
	})
	return srv, db
}

func doJSON(t *testing.T, srv *httptest.Server, method, path string, body any) (int, map[string]any, []byte) {
	t.Helper()
	var rdr bytes.Buffer
	if body != nil {
		b, err := json.Marshal(body)
		if err != nil {
			t.Fatalf("marshal: %v", err)
		}
		rdr.Write(b)
	}
	req, err := http.NewRequest(method, srv.URL+path, &rdr)
	if err != nil {
		t.Fatalf("newreq: %v", err)
	}
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	res, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("do: %v", err)
	}
	defer res.Body.Close()
	raw := make([]byte, 0)
	buf := make([]byte, 4096)
	for {
		n, rerr := res.Body.Read(buf)
		if n > 0 {
			raw = append(raw, buf[:n]...)
		}
		if rerr != nil {
			break
		}
	}
	var parsed map[string]any
	if len(raw) > 0 {
		_ = json.Unmarshal(raw, &parsed)
	}
	return res.StatusCode, parsed, raw
}

// TestCreateGetUpdateDeleteFlow exercises the full lifecycle of a book.
func TestCreateGetUpdateDeleteFlow(t *testing.T) {
	srv, _ := newTestServer(t)

	// Create.
	book := map[string]any{"title": "The Go Approach", "author": "A. Linguist", "year": 2023, "isbn": "111-222"}
	status, parsed, _ := doJSON(t, srv, "POST", "/books", book)
	if status != http.StatusCreated {
		t.Fatalf("create: want 201, got %d (%v)", status, parsed)
	}
	id := int64(parsed["id"].(float64))
	if parsed["title"] != "The Go Approach" {
		t.Fatalf("create echoed wrong title: %v", parsed["title"])
	}

	// Get by id.
	status, parsed, _ = doJSON(t, srv, "GET", "/books/"+itoa(id), nil)
	if status != http.StatusOK || parsed["author"] != "A. Linguist" {
		t.Fatalf("get: want 200/author=A. Linguist, got %d %v", status, parsed)
	}

	// Update.
	updated := map[string]any{"title": "Updated Title", "author": "New Author", "year": 2024, "isbn": "333-444"}
	status, parsed, _ = doJSON(t, srv, "PUT", "/books/"+itoa(id), updated)
	if status != http.StatusOK || parsed["title"] != "Updated Title" {
		t.Fatalf("update: want 200/Updated Title, got %d %v", status, parsed)
	}

	// Delete.
	status, _, _ = doJSON(t, srv, "DELETE", "/books/"+itoa(id), nil)
	if status != http.StatusNoContent {
		t.Fatalf("delete: want 204, got %d", status)
	}
	// Confirm gone.
	status, _, _ = doJSON(t, srv, "GET", "/books/"+itoa(id), nil)
	if status != http.StatusNotFound {
		t.Fatalf("after delete: want 404, got %d", status)
	}
}

// TestValidationRejectsMissingFields verifies that title/author are required
// at both create and update paths.
func TestValidationRejectsMissingFields(t *testing.T) {
	srv, _ := newTestServer(t)

	cases := []struct {
		name string
		body map[string]any
	}{
		{"missing author", map[string]any{"title": "T", "year": 2000}},
		{"missing title", map[string]any{"author": "A", "year": 2000}},
		{"empty title", map[string]any{"title": "  ", "author": "A"}},
		{"empty author", map[string]any{"title": "T", "author": "   "}},
	}
	for _, c := range cases {
		t.Run("POST/"+c.name, func(t *testing.T) {
			status, parsed, _ := doJSON(t, srv, "POST", "/books", c.body)
			if status != http.StatusBadRequest {
				t.Fatalf("create %s: want 400, got %d (%v)", c.name, status, parsed)
			}
		})
	}

	// Create a valid book first to test PUT validation.
	book := map[string]any{"title": "Valid", "author": "V"}
	status, parsed, _ := doJSON(t, srv, "POST", "/books", book)
	if status != http.StatusCreated {
		t.Fatalf("seed: want 201, got %d", status)
	}
	id := itoa(int64(parsed["id"].(float64)))

	for _, c := range cases {
		t.Run("PUT/"+c.name, func(t *testing.T) {
			status, _, _ := doJSON(t, srv, "PUT", "/books/"+id, c.body)
			if status != http.StatusBadRequest {
				t.Fatalf("update %s: want 400, got %d", c.name, status)
			}
		})
	}
}

// TestListAndAuthorFilter checks the list endpoint, the health check, and
// the ?author= query filter.
func TestListAndAuthorFilter(t *testing.T) {
	srv, _ := newTestServer(t)

	// Health.
	status, parsed, _ := doJSON(t, srv, "GET", "/health", nil)
	if status != http.StatusOK || parsed["status"] != "ok" {
		t.Fatalf("health: want 200/ok, got %d %v", status, parsed)
	}

	// Seed two books.
	seed := []map[string]any{
		{"title": "Alpha", "author": "Tolkien", "year": 1954, "isbn": "a1"},
		{"title": "Beta", "author": "Asimov", "year": 1951, "isbn": "b1"},
		{"title": "Gamma", "author": "Tolkien", "year": 1937, "isbn": "g1"},
	}
	for _, b := range seed {
		if s, _, _ := doJSON(t, srv, "POST", "/books", b); s != http.StatusCreated {
			t.Fatalf("seed create: want 201, got %d", s)
		}
	}

	// List all = 3.
	status, parsed, _ = doJSON(t, srv, "GET", "/books", nil)
	if status != http.StatusOK || int(parsed["count"].(float64)) != 3 {
		t.Fatalf("list all: want 200/count=3, got %d %v", status, parsed)
	}

	// Filter author=Tolkien -> 2.
	status, parsed, _ = doJSON(t, srv, "GET", "/books?author=Tolkien", nil)
	if status != http.StatusOK || int(parsed["count"].(float64)) != 2 {
		t.Fatalf("filter Tolkien: want 200/count=2, got %d %v", status, parsed)
	}

	// Filter author=Asimov -> 1.
	status, parsed, _ = doJSON(t, srv, "GET", "/books?author=Asimov", nil)
	if status != http.StatusOK || int(parsed["count"].(float64)) != 1 {
		t.Fatalf("filter Asimov: want 200/count=1, got %d %v", status, parsed)
	}

	// Filter author=NoSuch -> 0.
	status, parsed, _ = doJSON(t, srv, "GET", "/books?author=NoSuch", nil)
	if status != http.StatusOK || int(parsed["count"].(float64)) != 0 {
		t.Fatalf("filter none: want 200/count=0, got %d %v", status, parsed)
	}
}

// TestInvalidIDAndUnknownFields covers path-id validation and strict body
// decoding.
func TestInvalidIDAndUnknownFields(t *testing.T) {
	srv, _ := newTestServer(t)

	// Non-numeric id should be 400 not 404.
	if s, _, _ := doJSON(t, srv, "GET", "/books/abc", nil); s != http.StatusBadRequest {
		t.Fatalf("non-numeric id: want 400, got %d", s)
	}
	// Zero/negative id from path can't happen via HTTP, but unknown id => 404.
	if s, _, _ := doJSON(t, srv, "GET", "/books/9999", nil); s != http.StatusNotFound {
		t.Fatalf("unknown id: want 404, got %d", s)
	}
	// Unknown JSON field should be rejected.
	bad := map[string]any{"title": "T", "author": "A", "bogus": 1}
	if s, p, _ := doJSON(t, srv, "POST", "/books", bad); s != http.StatusBadRequest {
		t.Fatalf("unknown field: want 400, got %d (%v)", s, p)
	}
	// Empty body should be 400.
	if s, _, _ := doJSON(t, srv, "POST", "/books", nil); s != http.StatusBadRequest {
		t.Fatalf("empty body: want 400, got %d", s)
	}
}

// itoa is a small helper to avoid importing strconv everywhere.
func itoa(n int64) string {
	if n == 0 {
		return "0"
	}
	neg := n < 0
	if neg {
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
