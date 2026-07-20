package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"testing"
)

// newTestServer builds the full handler stack on top of a throwaway SQLite
// database in a temp directory.
func newTestServer(t *testing.T) http.Handler {
	t.Helper()
	store, err := OpenStore(filepath.Join(t.TempDir(), "test.db"))
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewServer(store).Routes()
}

func doRequest(t *testing.T, h http.Handler, method, path string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var buf bytes.Buffer
	if body != nil {
		if err := json.NewEncoder(&buf).Encode(body); err != nil {
			t.Fatalf("encode request body: %v", err)
		}
	}
	req := httptest.NewRequest(method, path, &buf)
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func decodeResponse[T any](t *testing.T, rec *httptest.ResponseRecorder) T {
	t.Helper()
	var v T
	if err := json.Unmarshal(rec.Body.Bytes(), &v); err != nil {
		t.Fatalf("decode response %q: %v", rec.Body.String(), err)
	}
	return v
}

func createBook(t *testing.T, h http.Handler, in bookInput) Book {
	t.Helper()
	rec := doRequest(t, h, http.MethodPost, "/books", in)
	if rec.Code != http.StatusCreated {
		t.Fatalf("create book: got status %d, body %s", rec.Code, rec.Body)
	}
	return decodeResponse[Book](t, rec)
}

func TestHealth(t *testing.T) {
	h := newTestServer(t)
	rec := doRequest(t, h, http.MethodGet, "/health", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("got status %d, want %d", rec.Code, http.StatusOK)
	}
	body := decodeResponse[map[string]string](t, rec)
	if body["status"] != "ok" {
		t.Fatalf("got body %v, want status ok", body)
	}
}

func TestCreateBook(t *testing.T) {
	h := newTestServer(t)
	b := createBook(t, h, bookInput{
		Title:  "The Go Programming Language",
		Author: "Alan Donovan",
		Year:   2015,
		ISBN:   "978-0134190440",
	})
	if b.ID == 0 {
		t.Error("expected non-zero ID")
	}
	if b.Title != "The Go Programming Language" || b.Author != "Alan Donovan" || b.Year != 2015 || b.ISBN != "978-0134190440" {
		t.Errorf("unexpected book: %+v", b)
	}
}

func TestCreateBookValidation(t *testing.T) {
	h := newTestServer(t)
	cases := []struct {
		name string
		in   bookInput
	}{
		{"missing title", bookInput{Author: "Someone"}},
		{"missing author", bookInput{Title: "Something"}},
		{"blank title", bookInput{Title: "  ", Author: "Someone"}},
		{"empty", bookInput{}},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			rec := doRequest(t, h, http.MethodPost, "/books", tc.in)
			if rec.Code != http.StatusBadRequest {
				t.Fatalf("got status %d, want %d", rec.Code, http.StatusBadRequest)
			}
			body := decodeResponse[errorResponse](t, rec)
			if body.Error == "" {
				t.Error("expected error message in response")
			}
		})
	}
}

func TestListBooksWithAuthorFilter(t *testing.T) {
	h := newTestServer(t)
	createBook(t, h, bookInput{Title: "Book A", Author: "Octavia Butler", Year: 1993})
	createBook(t, h, bookInput{Title: "Book B", Author: "Ursula Le Guin", Year: 1969})
	createBook(t, h, bookInput{Title: "Book C", Author: "Octavia Butler", Year: 1998})

	rec := doRequest(t, h, http.MethodGet, "/books", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("got status %d, want %d", rec.Code, http.StatusOK)
	}
	all := decodeResponse[[]Book](t, rec)
	if len(all) != 3 {
		t.Fatalf("got %d books, want 3", len(all))
	}

	rec = doRequest(t, h, http.MethodGet, "/books?author=Octavia+Butler", nil)
	filtered := decodeResponse[[]Book](t, rec)
	if len(filtered) != 2 {
		t.Fatalf("got %d filtered books, want 2", len(filtered))
	}
	for _, b := range filtered {
		if b.Author != "Octavia Butler" {
			t.Errorf("unexpected author %q in filtered result", b.Author)
		}
	}
}

func TestGetBook(t *testing.T) {
	h := newTestServer(t)
	created := createBook(t, h, bookInput{Title: "Dune", Author: "Frank Herbert", Year: 1965})

	rec := doRequest(t, h, http.MethodGet, fmt.Sprintf("/books/%d", created.ID), nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("got status %d, want %d", rec.Code, http.StatusOK)
	}
	got := decodeResponse[Book](t, rec)
	if got != created {
		t.Errorf("got %+v, want %+v", got, created)
	}
}

func TestGetBookNotFound(t *testing.T) {
	h := newTestServer(t)
	rec := doRequest(t, h, http.MethodGet, "/books/9999", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("got status %d, want %d", rec.Code, http.StatusNotFound)
	}
}

func TestUpdateBook(t *testing.T) {
	h := newTestServer(t)
	created := createBook(t, h, bookInput{Title: "Draft", Author: "Author", Year: 2000})

	rec := doRequest(t, h, http.MethodPut, fmt.Sprintf("/books/%d", created.ID), bookInput{
		Title:  "Revised",
		Author: "Author",
		Year:   2001,
		ISBN:   "123",
	})
	if rec.Code != http.StatusOK {
		t.Fatalf("got status %d, want %d; body %s", rec.Code, http.StatusOK, rec.Body)
	}
	updated := decodeResponse[Book](t, rec)
	if updated.ID != created.ID || updated.Title != "Revised" || updated.Year != 2001 || updated.ISBN != "123" {
		t.Errorf("unexpected updated book: %+v", updated)
	}

	// Confirm the change persisted.
	rec = doRequest(t, h, http.MethodGet, fmt.Sprintf("/books/%d", created.ID), nil)
	got := decodeResponse[Book](t, rec)
	if got.Title != "Revised" {
		t.Errorf("persisted title %q, want %q", got.Title, "Revised")
	}
}

func TestUpdateBookNotFound(t *testing.T) {
	h := newTestServer(t)
	rec := doRequest(t, h, http.MethodPut, "/books/9999", bookInput{Title: "T", Author: "A"})
	if rec.Code != http.StatusNotFound {
		t.Fatalf("got status %d, want %d", rec.Code, http.StatusNotFound)
	}
}

func TestDeleteBook(t *testing.T) {
	h := newTestServer(t)
	created := createBook(t, h, bookInput{Title: "Gone", Author: "Author"})

	rec := doRequest(t, h, http.MethodDelete, fmt.Sprintf("/books/%d", created.ID), nil)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("got status %d, want %d", rec.Code, http.StatusNoContent)
	}

	rec = doRequest(t, h, http.MethodGet, fmt.Sprintf("/books/%d", created.ID), nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("after delete got status %d, want %d", rec.Code, http.StatusNotFound)
	}
}

func TestDeleteBookNotFound(t *testing.T) {
	h := newTestServer(t)
	rec := doRequest(t, h, http.MethodDelete, "/books/9999", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("got status %d, want %d", rec.Code, http.StatusNotFound)
	}
}
