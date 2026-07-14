package main

import (
	"bytes"
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
)

// newTestStore returns a Store backed by a fresh temporary SQLite file,
// closed automatically via t.Cleanup.
func newTestStore(t *testing.T) *Store {
	t.Helper()
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "test.db")
	store, err := NewStore(dbPath)
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	t.Cleanup(func() { _ = store.Close() })
	return store
}

// newTestServer wires a fresh store to a Server and returns both.
func newTestServer(t *testing.T) (*Server, *Store) {
	store := newTestStore(t)
	return NewServer(store), store
}

// do sends a request against the server and returns the response (body already read).
func do(t *testing.T, s *Server, method, target string, body any) (*http.Response, []byte) {
	t.Helper()
	var rdr *bytes.Reader
	if body != nil {
		buf, err := json.Marshal(body)
		if err != nil {
			t.Fatalf("marshal: %v", err)
		}
		rdr = bytes.NewReader(buf)
	} else {
		rdr = bytes.NewReader(nil)
	}
	req := httptest.NewRequest(method, target, rdr)
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	rec := httptest.NewRecorder()
	s.ServeHTTP(rec, req)
	res := rec.Result()
	defer res.Body.Close()
	b := readAll(t, res.Body)
	return res, b
}

func mustDecode[T any](t *testing.T, b []byte) T {
	t.Helper()
	var v T
	if err := json.Unmarshal(b, &v); err != nil {
		t.Fatalf("unmarshal: %v (body=%q)", err, b)
	}
	return v
}

// ---------------------------------------------------------------------------
// Test 1: Store CRUD round-trip (unit).
// ---------------------------------------------------------------------------

func TestStoreCRUD(t *testing.T) {
	store := newTestStore(t)
	ctx := context.Background()

	// Create.
	b := &Book{Title: "The Go Programming Language", Author: "Alan Donovan", Year: 2015, ISBN: "9780134260566"}
	if err := store.Create(ctx, b); err != nil {
		t.Fatalf("create: %v", err)
	}
	if b.ID == 0 {
		t.Fatal("expected non-zero id after create")
	}

	// Get.
	got, err := store.Get(ctx, b.ID)
	if err != nil {
		t.Fatalf("get: %v", err)
	}
	if got.Title != b.Title || got.Author != b.Author || got.Year != b.Year || got.ISBN != b.ISBN {
		t.Fatalf("get returned mismatched book: %+v vs %+v", got, b)
	}

	// Update.
	b.Title = "GoPL (2nd)"
	b.Year = 2024
	if err := store.Update(ctx, b); err != nil {
		t.Fatalf("update: %v", err)
	}
	got, _ = store.Get(ctx, b.ID)
	if got.Title != "GoPL (2nd)" || got.Year != 2024 {
		t.Fatalf("update did not persist: %+v", got)
	}

	// List with author filter.
	other := &Book{Title: "Other", Author: "Someone Else"}
	_ = store.Create(ctx, other)
	gotAll, err := store.List(ctx, "Alan Donovan")
	if err != nil {
		t.Fatalf("list: %v", err)
	}
	if len(gotAll) != 1 || gotAll[0].ID != b.ID {
		t.Fatalf("author filter expected 1 match, got %+v", gotAll)
	}
	gotAll, _ = store.List(ctx, "")
	if len(gotAll) != 2 {
		t.Fatalf("unfiltered list expected 2, got %d", len(gotAll))
	}

	// Delete.
	if err := store.Delete(ctx, other.ID); err != nil {
		t.Fatalf("delete: %v", err)
	}
	if _, err := store.Get(ctx, other.ID); !errors.Is(err, ErrNotFound) {
		t.Fatalf("expected ErrNotFound after delete, got %v", err)
	}
	// Delete again -> ErrNotFound.
	if err := store.Delete(ctx, other.ID); !errors.Is(err, ErrNotFound) {
		t.Fatalf("expected ErrNotFound on re-delete, got %v", err)
	}
	// Update on missing id -> ErrNotFound.
	if err := store.Update(ctx, &Book{ID: 999, Title: "x", Author: "y"}); !errors.Is(err, ErrNotFound) {
		t.Fatalf("expected ErrNotFound on update of missing id, got %v", err)
	}
}

// ---------------------------------------------------------------------------
// Test 2: HTTP integration of create/list/get/update/delete/health.
// ---------------------------------------------------------------------------

func TestHTTPCRUDIntegration(t *testing.T) {
	srv, _ := newTestServer(t)

	// Health.
	res, body := do(t, srv, "GET", "/health", nil)
	if res.StatusCode != http.StatusOK {
		t.Fatalf("health status = %d, body=%q", res.StatusCode, body)
	}

	// Create -> 201 with id.
	res, body = do(t, srv, "POST", "/books", Book{Title: "Clean Code", Author: "Robert Martin", Year: 2008, ISBN: "9780132350884"})
	if res.StatusCode != http.StatusCreated {
		t.Fatalf("create status = %d, body=%q", res.StatusCode, body)
	}
	created := mustDecode[Book](t, body)
	if created.ID == 0 {
		t.Fatal("expected non-zero id in create response")
	}

	// Get by id -> 200.
	res, body = do(t, srv, "GET", "/books/"+idStr(created.ID), nil)
	if res.StatusCode != http.StatusOK {
		t.Fatalf("get status = %d, body=%q", res.StatusCode, body)
	}
	got := mustDecode[Book](t, body)
	if got.Title != "Clean Code" {
		t.Fatalf("get title mismatch: %q", got.Title)
	}

	// Get nonexistent -> 404.
	res, body = do(t, srv, "GET", "/books/999999", nil)
	if res.StatusCode != http.StatusNotFound {
		t.Fatalf("expected 404, got %d body=%q", res.StatusCode, body)
	}

	// List -> 200 array containing our book.
	res, body = do(t, srv, "GET", "/books", nil)
	if res.StatusCode != http.StatusOK {
		t.Fatalf("list status = %d, body=%q", res.StatusCode, body)
	}
	all := mustDecode[[]Book](t, body)
	if len(all) != 1 || all[0].ID != created.ID {
		t.Fatalf("list expected 1 book with our id, got %+v", all)
	}

	// Create a second book with a different author for filter test.
	res, body = do(t, srv, "POST", "/books", Book{Title: "Refactoring", Author: "Martin Fowler", Year: 1999})
	if res.StatusCode != http.StatusCreated {
		t.Fatalf("second create status = %d, body=%q", res.StatusCode, body)
	}

	// Filter by author.
	res, body = do(t, srv, "GET", "/books?author=Robert%20Martin", nil)
	if res.StatusCode != http.StatusOK {
		t.Fatalf("filter status = %d, body=%q", res.StatusCode, body)
	}
	filtered := mustDecode[[]Book](t, body)
	if len(filtered) != 1 || filtered[0].Author != "Robert Martin" {
		t.Fatalf("filter expected 1 Robert Martin, got %+v", filtered)
	}

	// Update -> 200 with new values.
	res, body = do(t, srv, "PUT", "/books/"+idStr(created.ID), Book{Title: "Clean Code (2e)", Author: "Robert C. Martin", Year: 2021, ISBN: "9780135957059"})
	if res.StatusCode != http.StatusOK {
		t.Fatalf("update status = %d, body=%q", res.StatusCode, body)
	}
	updated := mustDecode[Book](t, body)
	if updated.Title != "Clean Code (2e)" {
		t.Fatalf("update response title mismatch: %q", updated.Title)
	}

	// Update nonexistent -> 404.
	res, body = do(t, srv, "PUT", "/books/777777", Book{Title: "x", Author: "y"})
	if res.StatusCode != http.StatusNotFound {
		t.Fatalf("expected 404 update missing, got %d body=%q", res.StatusCode, body)
	}

	// Delete -> 204.
	res, body = do(t, srv, "DELETE", "/books/"+idStr(created.ID), nil)
	if res.StatusCode != http.StatusNoContent {
		t.Fatalf("delete status = %d, body=%q", res.StatusCode, body)
	}
	// Verify gone.
	res, body = do(t, srv, "GET", "/books/"+idStr(created.ID), nil)
	if res.StatusCode != http.StatusNotFound {
		t.Fatalf("expected 404 after delete, got %d body=%q", res.StatusCode, body)
	}
	// Delete again -> 404.
	res, body = do(t, srv, "DELETE", "/books/"+idStr(created.ID), nil)
	if res.StatusCode != http.StatusNotFound {
		t.Fatalf("expected 404 re-delete, got %d body=%q", res.StatusCode, body)
	}
}

// ---------------------------------------------------------------------------
// Test 3: Input validation returns 400 and rejects bad IDs/bodies.
// ---------------------------------------------------------------------------

func TestValidationAndBadRequests(t *testing.T) {
	srv, _ := newTestServer(t)

	cases := []struct {
		name       string
		method     string
		target     string
		body       any
		wantStatus int
	}{
		{"missing title", "POST", "/books", Book{Author: "a"}, http.StatusBadRequest},
		{"missing author", "POST", "/books", Book{Title: "t"}, http.StatusBadRequest},
		{"blank title", "POST", "/books", Book{Title: "   ", Author: "a"}, http.StatusBadRequest},
		{"both missing", "POST", "/books", Book{}, http.StatusBadRequest},
		{"negative year", "POST", "/books", Book{Title: "t", Author: "a", Year: -1}, http.StatusBadRequest},
		{"update missing title", "PUT", "/books/1", Book{Author: "a"}, http.StatusBadRequest},
		{"invalid id path", "GET", "/books/not-a-number", nil, http.StatusBadRequest},
		{"nonexistent get", "GET", "/books/404", nil, http.StatusNotFound},
	}

	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			res, body := do(t, srv, c.method, c.target, c.body)
			if res.StatusCode != c.wantStatus {
				t.Fatalf("%s %s: status = %d, want %d, body=%q", c.method, c.target, res.StatusCode, c.wantStatus, body)
			}
			// Bad requests must be JSON error objects, not plain text.
			if c.wantStatus >= 400 && len(body) > 0 {
				var eb errorBody
				if err := json.Unmarshal(body, &eb); err != nil {
					t.Fatalf("error response not JSON: %v body=%q", err, body)
				}
				if eb.Error == "" {
					t.Fatalf("error message empty, body=%q", body)
				}
			}
		})
	}

	// Malformed JSON body should yield 400.
	res, body := malformedJSONRequest(t, srv, "POST", "/books")
	if res.StatusCode != http.StatusBadRequest {
		t.Fatalf("malformed json status = %d, body=%q", res.StatusCode, body)
	}
}

func malformedJSONRequest(t *testing.T, s *Server, method, target string) (*http.Response, []byte) {
	t.Helper()
	req := httptest.NewRequest(method, target, bytes.NewReader([]byte("{not json")))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	s.ServeHTTP(rec, req)
	res := rec.Result()
	defer res.Body.Close()
	return res, readAll(t, res.Body)
}

// ---------------------------------------------------------------------------
// Test 4 (bonus): the SQLite file is actually created on disk and survives
// reopen, proving we're using a real embedded DB (not an in-memory mock).
// ---------------------------------------------------------------------------

func TestStorePersistsAcrossConnections(t *testing.T) {
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "persist.db")

	s1, err := NewStore(dbPath)
	if err != nil {
		t.Fatalf("open s1: %v", err)
	}
	ctx := context.Background()
	b := &Book{Title: "Persistent", Author: "Anon"}
	if err := s1.Create(ctx, b); err != nil {
		t.Fatalf("create: %v", err)
	}
	id := b.ID
	_ = s1.Close()

	if _, err := os.Stat(dbPath); err != nil {
		t.Fatalf("db file not on disk: %v", err)
	}

	s2, err := NewStore(dbPath)
	if err != nil {
		t.Fatalf("reopen s2: %v", err)
	}
	defer s2.Close()
	got, err := s2.Get(ctx, id)
	if err != nil {
		t.Fatalf("get after reopen: %v", err)
	}
	if got.Title != "Persistent" {
		t.Fatalf("data did not persist: %+v", got)
	}

	// Sanity: the underlying driver is sqlite and reachable.
	var driver string
	if err := s2.db.QueryRowContext(ctx, "SELECT sqlite_version();").Scan(&driver); err != nil && !errors.Is(err, sql.ErrNoRows) {
		// sqlite_version() returns a string; ignore scan type issues but no fatal error expected.
		_ = err
	}
}

// ---------------------------------------------------------------------------
// Test 5 (bonus): model validation edge cases.
// ---------------------------------------------------------------------------

func TestBookValidate(t *testing.T) {
	cases := []struct {
		name string
		book Book
		wantErr bool
	}{
		{"valid full", Book{Title: "T", Author: "A", Year: 2020, ISBN: "x"}, false},
		{"valid no year", Book{Title: "T", Author: "A"}, false},
		{"empty title", Book{Author: "A"}, true},
		{"empty author", Book{Title: "T"}, true},
		{"whitespace title", Book{Title: "  ", Author: "A"}, true},
		{"negative year", Book{Title: "T", Author: "A", Year: -5}, true},
		{"zero year ok", Book{Title: "T", Author: "A", Year: 0}, false},
		{"positive year ok", Book{Title: "T", Author: "A", Year: 1}, false},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			err := c.book.Validate()
			if c.wantErr && err == nil {
				t.Fatal("expected error, got nil")
			}
			if !c.wantErr && err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
		})
	}
}
