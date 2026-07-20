package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strconv"
	"testing"
)

// newTestServer spins up a Server backed by a fresh temp-file SQLite DB.
func newTestServer(t *testing.T) *Server {
	t.Helper()
	store, err := NewStore(filepath.Join(t.TempDir(), "test.db"))
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewServer(store)
}

// doRequest issues an HTTP request against the test server and returns the recorder.
func doRequest(t *testing.T, srv *Server, method, target string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var buf bytes.Buffer
	if body != nil {
		if err := json.NewEncoder(&buf).Encode(body); err != nil {
			t.Fatalf("encode body: %v", err)
		}
	}
	req := httptest.NewRequest(method, target, &buf)
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	srv.ServeHTTP(rec, req)
	return rec
}

// decodeBody unmarshals a recorder body into v.
func decodeBody(t *testing.T, rec *httptest.ResponseRecorder, v any) {
	t.Helper()
	if err := json.NewDecoder(rec.Body).Decode(v); err != nil {
		t.Fatalf("decode response: %v (body: %q)", err, rec.Body.String())
	}
}

func createBook(t *testing.T, srv *Server, b Book) Book {
	t.Helper()
	rec := doRequest(t, srv, http.MethodPost, "/books", b)
	if rec.Code != http.StatusCreated {
		t.Fatalf("create %v: got %d, want 201 (body: %s)", b, rec.Code, rec.Body.String())
	}
	var created Book
	decodeBody(t, rec, &created)
	return created
}

func TestHealth(t *testing.T) {
	srv := newTestServer(t)
	rec := doRequest(t, srv, http.MethodGet, "/health", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("got %d, want 200", rec.Code)
	}
	var body map[string]string
	decodeBody(t, rec, &body)
	if body["status"] != "ok" {
		t.Fatalf("got status %q, want %q", body["status"], "ok")
	}
}

func TestCreateBook(t *testing.T) {
	srv := newTestServer(t)
	created := createBook(t, srv, Book{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441172719"})
	if created.ID == 0 {
		t.Fatal("expected assigned ID, got 0")
	}
	if created.Title != "Dune" || created.Author != "Frank Herbert" || created.Year != 1965 || created.ISBN != "9780441172719" {
		t.Fatalf("round-trip mismatch: %+v", created)
	}
	if ct := rec_ContentType(t, srv); ct != "application/json" {
		t.Fatalf("content-type %q, want application/json", ct)
	}
}

// rec_ContentType fetches /health and returns its Content-Type header.
func rec_ContentType(t *testing.T, srv *Server) string {
	t.Helper()
	rec := doRequest(t, srv, http.MethodGet, "/health", nil)
	return rec.Header().Get("Content-Type")
}

func TestCreateBookValidation(t *testing.T) {
	srv := newTestServer(t)

	cases := []struct {
		name string
		book Book
	}{
		{"missing title", Book{Author: "Someone", Year: 2000}},
		{"missing author", Book{Title: "Something", Year: 2000}},
		{"blank title", Book{Title: "   ", Author: "Someone"}},
		{"blank author", Book{Title: "Something", Author: ""}},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			rec := doRequest(t, srv, http.MethodPost, "/books", tc.book)
			if rec.Code != http.StatusBadRequest {
				t.Fatalf("got %d, want 400 (body: %s)", rec.Code, rec.Body.String())
			}
			var body map[string]string
			decodeBody(t, rec, &body)
			if body["error"] == "" {
				t.Fatal("expected error message in response")
			}
		})
	}

	// Malformed JSON is also a 400.
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBufferString("{not json"))
	rec := httptest.NewRecorder()
	srv.ServeHTTP(rec, req)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("malformed JSON: got %d, want 400", rec.Code)
	}
}

func TestListBooksWithAuthorFilter(t *testing.T) {
	srv := newTestServer(t)
	createBook(t, srv, Book{Title: "Dune", Author: "Frank Herbert", Year: 1965})
	createBook(t, srv, Book{Title: "Dune Messiah", Author: "Frank Herbert", Year: 1969})
	createBook(t, srv, Book{Title: "The Hobbit", Author: "J.R.R. Tolkien", Year: 1937})

	// Unfiltered: all three.
	rec := doRequest(t, srv, http.MethodGet, "/books", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("got %d, want 200", rec.Code)
	}
	var all []Book
	decodeBody(t, rec, &all)
	if len(all) != 3 {
		t.Fatalf("got %d books, want 3", len(all))
	}

	// Filtered: only Herbert's two.
	rec = doRequest(t, srv, http.MethodGet, "/books?author=Frank+Herbert", nil)
	var filtered []Book
	decodeBody(t, rec, &filtered)
	if len(filtered) != 2 {
		t.Fatalf("got %d books, want 2", len(filtered))
	}
	for _, b := range filtered {
		if b.Author != "Frank Herbert" {
			t.Fatalf("filter leaked author %q", b.Author)
		}
	}

	// Filter with no matches: empty array (not null).
	rec = doRequest(t, srv, http.MethodGet, "/books?author=Nobody", nil)
	var none []Book
	decodeBody(t, rec, &none)
	if len(none) != 0 {
		t.Fatalf("got %d books, want 0", len(none))
	}
}

func TestGetBook(t *testing.T) {
	srv := newTestServer(t)
	created := createBook(t, srv, Book{Title: "Dune", Author: "Frank Herbert"})

	rec := doRequest(t, srv, http.MethodGet, "/books/"+itoa(created.ID), nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("got %d, want 200", rec.Code)
	}
	var got Book
	decodeBody(t, rec, &got)
	if got != created {
		t.Fatalf("got %+v, want %+v", got, created)
	}

	// Missing ID -> 404.
	rec = doRequest(t, srv, http.MethodGet, "/books/9999", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("got %d, want 404", rec.Code)
	}

	// Non-numeric ID -> 400.
	rec = doRequest(t, srv, http.MethodGet, "/books/abc", nil)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("got %d, want 400", rec.Code)
	}
}

func TestUpdateBook(t *testing.T) {
	srv := newTestServer(t)
	created := createBook(t, srv, Book{Title: "Dne", Author: "Frank Herbert", Year: 1965})

	rec := doRequest(t, srv, http.MethodPut, "/books/"+itoa(created.ID),
		Book{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441172719"})
	if rec.Code != http.StatusOK {
		t.Fatalf("got %d, want 200 (body: %s)", rec.Code, rec.Body.String())
	}
	var updated Book
	decodeBody(t, rec, &updated)
	if updated.ID != created.ID || updated.Title != "Dune" || updated.ISBN != "9780441172719" {
		t.Fatalf("unexpected update result: %+v", updated)
	}

	// Persisted?
	rec = doRequest(t, srv, http.MethodGet, "/books/"+itoa(created.ID), nil)
	var got Book
	decodeBody(t, rec, &got)
	if got.Title != "Dune" {
		t.Fatalf("update not persisted: %+v", got)
	}

	// Updating a missing book -> 404.
	rec = doRequest(t, srv, http.MethodPut, "/books/9999", Book{Title: "X", Author: "Y"})
	if rec.Code != http.StatusNotFound {
		t.Fatalf("got %d, want 404", rec.Code)
	}

	// Invalid payload -> 400.
	rec = doRequest(t, srv, http.MethodPut, "/books/"+itoa(created.ID), Book{Author: "Y"})
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("got %d, want 400", rec.Code)
	}
}

func TestDeleteBook(t *testing.T) {
	srv := newTestServer(t)
	created := createBook(t, srv, Book{Title: "Dune", Author: "Frank Herbert"})

	rec := doRequest(t, srv, http.MethodDelete, "/books/"+itoa(created.ID), nil)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("got %d, want 204", rec.Code)
	}

	// Gone for good.
	rec = doRequest(t, srv, http.MethodGet, "/books/"+itoa(created.ID), nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("got %d, want 404 after delete", rec.Code)
	}

	// Second delete -> 404.
	rec = doRequest(t, srv, http.MethodDelete, "/books/"+itoa(created.ID), nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("got %d, want 404", rec.Code)
	}
}

func itoa(id int64) string {
	return strconv.FormatInt(id, 10)
}
