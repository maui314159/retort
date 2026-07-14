package main

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
)

func setupTestServer(t *testing.T) *server {
	t.Helper()
	db, err := openDB(":memory:")
	if err != nil {
		t.Fatalf("open test db: %v", err)
	}
	t.Cleanup(func() { db.Close() })
	if err := migrate(db); err != nil {
		t.Fatalf("migrate test db: %v", err)
	}
	return newServer(db)
}

func TestHealth(t *testing.T) {
	s := setupTestServer(t)
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	rec := httptest.NewRecorder()
	s.router().ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected status %d, got %d", http.StatusOK, rec.Code)
	}
	body := decodeBody[HealthResponse](t, rec.Body.Bytes())
	if body.Status != "ok" {
		t.Fatalf("expected status ok, got %q", body.Status)
	}
}

func TestCreateBook(t *testing.T) {
	s := setupTestServer(t)
	book := Book{Title: "The Go Programming Language", Author: "Alan Donovan", Year: 2015, ISBN: "978-0134190440"}
	rec := doRequest(t, s, http.MethodPost, "/books", book)

	if rec.Code != http.StatusCreated {
		t.Fatalf("expected status %d, got %d", http.StatusCreated, rec.Code)
	}
	created := decodeBody[Book](t, rec.Body.Bytes())
	if created.ID == 0 {
		t.Fatal("expected created book to have an id")
	}
	if created.Title != book.Title || created.Author != book.Author {
		t.Fatalf("created book mismatch: got %+v", created)
	}
}

func TestCreateBookValidation(t *testing.T) {
	s := setupTestServer(t)
	cases := []struct {
		name string
		book Book
	}{
		{"missing title", Book{Author: "Alan Donovan"}},
		{"missing author", Book{Title: "The Go Programming Language"}},
		{"empty title", Book{Title: "   ", Author: "Alan Donovan"}},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			rec := doRequest(t, s, http.MethodPost, "/books", tc.book)
			if rec.Code != http.StatusBadRequest {
				t.Fatalf("expected status %d, got %d", http.StatusBadRequest, rec.Code)
			}
		})
	}
}

func TestListAndFilterBooks(t *testing.T) {
	s := setupTestServer(t)
	createBook(t, s, Book{Title: "Book A", Author: "Alice"})
	createBook(t, s, Book{Title: "Book B", Author: "Bob"})
	createBook(t, s, Book{Title: "Book C", Author: "Alice Smith"})

	rec := doRequest(t, s, http.MethodGet, "/books", nil)
	all := decodeBody[[]Book](t, rec.Body.Bytes())
	if len(all) != 3 {
		t.Fatalf("expected 3 books, got %d", len(all))
	}

	rec = doRequest(t, s, http.MethodGet, "/books?author=Alice", nil)
	filtered := decodeBody[[]Book](t, rec.Body.Bytes())
	if len(filtered) != 2 {
		t.Fatalf("expected 2 books matching Alice, got %d", len(filtered))
	}
}

func TestGetUpdateDeleteBook(t *testing.T) {
	s := setupTestServer(t)
	created := createBook(t, s, Book{Title: "Original", Author: "Author"})

	// GET
	rec := doRequest(t, s, http.MethodGet, "/books/"+itoa(created.ID), nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected status %d, got %d", http.StatusOK, rec.Code)
	}
	got := decodeBody[Book](t, rec.Body.Bytes())
	if got.ID != created.ID {
		t.Fatalf("expected book id %d, got %d", created.ID, got.ID)
	}

	// GET not found
	rec = doRequest(t, s, http.MethodGet, "/books/9999", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("expected status %d, got %d", http.StatusNotFound, rec.Code)
	}

	// PUT
	updated := Book{Title: "Updated", Author: "New Author", Year: 2024, ISBN: "123"}
	rec = doRequest(t, s, http.MethodPut, "/books/"+itoa(created.ID), updated)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected status %d, got %d", http.StatusOK, rec.Code)
	}
	gotUpdated := decodeBody[Book](t, rec.Body.Bytes())
	if gotUpdated.Title != updated.Title || gotUpdated.Year != updated.Year {
		t.Fatalf("updated book mismatch: got %+v", gotUpdated)
	}

	// PUT not found
	rec = doRequest(t, s, http.MethodPut, "/books/9999", updated)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("expected status %d, got %d", http.StatusNotFound, rec.Code)
	}

	// DELETE
	rec = doRequest(t, s, http.MethodDelete, "/books/"+itoa(created.ID), nil)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("expected status %d, got %d", http.StatusNoContent, rec.Code)
	}

	// DELETE not found
	rec = doRequest(t, s, http.MethodDelete, "/books/"+itoa(created.ID), nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("expected status %d, got %d", http.StatusNotFound, rec.Code)
	}
}

func createBook(t *testing.T, s *server, book Book) Book {
	t.Helper()
	rec := doRequest(t, s, http.MethodPost, "/books", book)
	if rec.Code != http.StatusCreated {
		t.Fatalf("create book failed: status %d, body %s", rec.Code, rec.Body.String())
	}
	return decodeBody[Book](t, rec.Body.Bytes())
}

func doRequest(t *testing.T, s *server, method, path string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var r io.Reader
	if body != nil {
		b, err := json.Marshal(body)
		if err != nil {
			t.Fatalf("marshal body: %v", err)
		}
		r = bytes.NewReader(b)
	}
	req := httptest.NewRequest(method, path, r)
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	s.router().ServeHTTP(rec, req)
	return rec
}

func decodeBody[T any](t *testing.T, body []byte) T {
	t.Helper()
	var v T
	if err := json.Unmarshal(body, &v); err != nil {
		t.Fatalf("decode body %q: %v", string(body), err)
	}
	return v
}

func itoa(n int64) string {
	var buf [20]byte
	i := len(buf)
	if n == 0 {
		return "0"
	}
	neg := n < 0
	if neg {
		n = -n
	}
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
