package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func newTestServer(t *testing.T) *Server {
	t.Helper()
	srv, err := NewServer(":memory:")
	if err != nil {
		t.Fatalf("new server: %v", err)
	}
	t.Cleanup(func() { srv.Close() })
	return srv
}

func doRequest(t *testing.T, h http.Handler, method, path string, body interface{}) *httptest.ResponseRecorder {
	t.Helper()
	var buf bytes.Buffer
	if body != nil {
		if err := json.NewEncoder(&buf).Encode(body); err != nil {
			t.Fatalf("encode body: %v", err)
		}
	}
	req := httptest.NewRequest(method, path, &buf)
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func TestCreateGetBook(t *testing.T) {
	srv := newTestServer(t)
	h := srv.Routes()

	in := Book{Title: "The Go Book", Author: "A. Author", Year: 2020, ISBN: "1234567890"}
	rec := doRequest(t, h, http.MethodPost, "/books", in)
	if rec.Code != http.StatusCreated {
		t.Fatalf("expected 201, got %d: %s", rec.Code, rec.Body.String())
	}
	var created Book
	if err := json.NewDecoder(rec.Body).Decode(&created); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if created.ID == 0 {
		t.Fatal("expected non-zero id")
	}
	if created.Title != in.Title {
		t.Fatalf("expected title %q, got %q", in.Title, created.Title)
	}

	rec = doRequest(t, h, http.MethodGet, "/books/1", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
	var got Book
	if err := json.NewDecoder(rec.Body).Decode(&got); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if got.Title != in.Title || got.ISBN != in.ISBN {
		t.Fatalf("unexpected book: %+v", got)
	}
}

func TestValidationErrors(t *testing.T) {
	srv := newTestServer(t)
	h := srv.Routes()

	cases := []struct {
		name string
		body Book
	}{
		{"missing title", Book{Author: "X"}},
		{"missing author", Book{Title: "Y"}},
		{"both empty", Book{}},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			rec := doRequest(t, h, http.MethodPost, "/books", c.body)
			if rec.Code != http.StatusBadRequest {
				t.Fatalf("expected 400, got %d: %s", rec.Code, rec.Body.String())
			}
		})
	}
}

func TestListWithAuthorFilter(t *testing.T) {
	srv := newTestServer(t)
	h := srv.Routes()

	books := []Book{
		{Title: "A", Author: "Alice", Year: 2001, ISBN: "i1"},
		{Title: "B", Author: "Bob", Year: 2002, ISBN: "i2"},
		{Title: "C", Author: "Alice", Year: 2003, ISBN: "i3"},
	}
	for _, b := range books {
		rec := doRequest(t, h, http.MethodPost, "/books", b)
		if rec.Code != http.StatusCreated {
			t.Fatalf("create failed: %d %s", rec.Code, rec.Body.String())
		}
	}

	rec := doRequest(t, h, http.MethodGet, "/books?author=Alice", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
	var got []Book
	if err := json.NewDecoder(rec.Body).Decode(&got); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if len(got) != 2 {
		t.Fatalf("expected 2 books, got %d", len(got))
	}
	for _, b := range got {
		if b.Author != "Alice" {
			t.Fatalf("expected Alice, got %q", b.Author)
		}
	}
}

func TestUpdateAndDelete(t *testing.T) {
	srv := newTestServer(t)
	h := srv.Routes()

	rec := doRequest(t, h, http.MethodPost, "/books", Book{Title: "Old", Author: "A", Year: 2000, ISBN: "x"})
	if rec.Code != http.StatusCreated {
		t.Fatalf("create: %d %s", rec.Code, rec.Body.String())
	}

	rec = doRequest(t, h, http.MethodPut, "/books/1", Book{Title: "New", Author: "B", Year: 2010, ISBN: "y"})
	if rec.Code != http.StatusOK {
		t.Fatalf("update: %d %s", rec.Code, rec.Body.String())
	}
	var updated Book
	if err := json.NewDecoder(rec.Body).Decode(&updated); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if updated.Title != "New" || updated.Author != "B" {
		t.Fatalf("unexpected update: %+v", updated)
	}

	rec = doRequest(t, h, http.MethodDelete, "/books/1", nil)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("delete: %d %s", rec.Code, rec.Body.String())
	}

	rec = doRequest(t, h, http.MethodGet, "/books/1", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("expected 404 after delete, got %d", rec.Code)
	}
}

func TestHealth(t *testing.T) {
	srv := newTestServer(t)
	h := srv.Routes()
	rec := doRequest(t, h, http.MethodGet, "/health", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
}
