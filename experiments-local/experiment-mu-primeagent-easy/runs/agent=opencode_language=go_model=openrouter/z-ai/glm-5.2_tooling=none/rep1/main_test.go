package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func newTestServer(t *testing.T) (*Server, func()) {
	t.Helper()
	store, err := NewStore(":memory:")
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	srv := NewServer(store)
	return srv, func() { store.Close() }
}

func doJSON(t *testing.T, srv http.Handler, method, target string, body any) *httptest.ResponseRecorder {
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

func TestCreateAndGetBook(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()

	rec := doJSON(t, srv, "POST", "/books", Book{Title: "The Go", Author: "A. Author", Year: 2020, ISBN: "111"})
	if rec.Code != http.StatusCreated {
		t.Fatalf("create: expected 201, got %d: %s", rec.Code, rec.Body.String())
	}
	var created Book
	if err := json.Unmarshal(rec.Body.Bytes(), &created); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if created.ID == 0 {
		t.Fatal("expected non-zero id")
	}

	rec = doJSON(t, srv, "GET", "/books/1", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("get: expected 200, got %d", rec.Code)
	}
	var got Book
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if got.Title != "The Go" {
		t.Fatalf("unexpected title: %s", got.Title)
	}
}

func TestValidationRejectsEmpty(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()

	rec := doJSON(t, srv, "POST", "/books", Book{Title: "", Author: "", Year: 2020, ISBN: "x"})
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", rec.Code)
	}
}

func TestListWithAuthorFilter(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()

	doJSON(t, srv, "POST", "/books", Book{Title: "A", Author: "Alice", Year: 2001, ISBN: "a"})
	doJSON(t, srv, "POST", "/books", Book{Title: "B", Author: "Bob", Year: 2002, ISBN: "b"})
	doJSON(t, srv, "POST", "/books", Book{Title: "C", Author: "Alice", Year: 2003, ISBN: "c"})

	rec := doJSON(t, srv, "GET", "/books?author=Alice", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("list: expected 200, got %d", rec.Code)
	}
	var books []Book
	if err := json.Unmarshal(rec.Body.Bytes(), &books); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if len(books) != 2 {
		t.Fatalf("expected 2 books for Alice, got %d", len(books))
	}
	for _, b := range books {
		if b.Author != "Alice" {
			t.Fatalf("unexpected author: %s", b.Author)
		}
	}
}

func TestUpdateAndDelete(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()

	rec := doJSON(t, srv, "POST", "/books", Book{Title: "T", Author: "A", Year: 2010, ISBN: "i"})
	var created Book
	json.Unmarshal(rec.Body.Bytes(), &created)

	rec = doJSON(t, srv, "PUT", "/books/1", Book{Title: "T2", Author: "A2", Year: 2011, ISBN: "i2"})
	if rec.Code != http.StatusOK {
		t.Fatalf("update: expected 200, got %d: %s", rec.Code, rec.Body.String())
	}

	rec = doJSON(t, srv, "DELETE", "/books/1", nil)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("delete: expected 204, got %d", rec.Code)
	}

	rec = doJSON(t, srv, "GET", "/books/1", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("get after delete: expected 404, got %d", rec.Code)
	}
}

func TestHealth(t *testing.T) {
	srv, cleanup := newTestServer(t)
	defer cleanup()
	rec := doJSON(t, srv, "GET", "/health", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("health: expected 200, got %d", rec.Code)
	}
}
