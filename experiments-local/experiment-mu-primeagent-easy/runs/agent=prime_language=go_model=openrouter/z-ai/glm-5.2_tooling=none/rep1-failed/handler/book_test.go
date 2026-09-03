package handler

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"

	"github.com/example/bookapi/model"
	"github.com/example/bookapi/store"

	_ "modernc.org/sqlite"
)

// newTestServer builds a handler backed by an in-memory SQLite database and
// returns an httptest server together with a cleanup function.
func newTestServer(t *testing.T) (*httptest.Server, *sql.DB) {
	t.Helper()
	db, err := sql.Open("sqlite", ":memory:")
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	// Keep a single connection so the in-memory database persists across
	// requests within the same test.
	db.SetMaxOpenConns(1)
	if err := store.InitSchema(db); err != nil {
		t.Fatalf("init schema: %v", err)
	}
	h := NewHandler(store.NewBookStore(db))
	mux := http.NewServeMux()
	mux.HandleFunc("POST /books", h.CreateBook)
	mux.HandleFunc("GET /books", h.ListBooks)
	mux.HandleFunc("GET /books/{id}", h.GetBook)
	mux.HandleFunc("PUT /books/{id}", h.UpdateBook)
	mux.HandleFunc("DELETE /books/{id}", h.DeleteBook)
	mux.HandleFunc("GET /health", h.Health)
	srv := httptest.NewServer(mux)
	t.Cleanup(func() {
		srv.Close()
		db.Close()
	})
	return srv, db
}

func doJSON(t *testing.T, method, url string, body any) *http.Response {
	t.Helper()
	var rdr io.Reader
	if body != nil {
		b, err := json.Marshal(body)
		if err != nil {
			t.Fatalf("marshal body: %v", err)
		}
		rdr = bytes.NewReader(b)
	}
	req, err := http.NewRequest(method, url, rdr)
	if err != nil {
		t.Fatalf("new request: %v", err)
	}
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("do request: %v", err)
	}
	return resp
}

func mustCreateBook(t *testing.T, srv *httptest.Server, in model.BookInput) model.Book {
	t.Helper()
	resp := doJSON(t, http.MethodPost, srv.URL+"/books", in)
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("expected 201, got %d", resp.StatusCode)
	}
	var b model.Book
	if err := json.NewDecoder(resp.Body).Decode(&b); err != nil {
		t.Fatalf("decode body: %v", err)
	}
	return b
}

// TestCreateAndGetBook verifies a book can be created and then retrieved.
func TestCreateAndGetBook(t *testing.T) {
	srv, _ := newTestServer(t)

	created := mustCreateBook(t, srv, model.BookInput{
		Title:  "The Go Programming Language",
		Author: "Alan Donovan",
		Year:   2015,
		ISBN:   "978-0134190440",
	})
	if created.ID <= 0 {
		t.Fatalf("expected positive id, got %d", created.ID)
	}
	if created.Title != "The Go Programming Language" {
		t.Fatalf("unexpected title: %q", created.Title)
	}

	resp := doJSON(t, http.MethodGet, srv.URL+"/books/"+strconv.Itoa(created.ID), nil)
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}
	var got model.Book
	if err := json.NewDecoder(resp.Body).Decode(&got); err != nil {
		t.Fatalf("decode body: %v", err)
	}
	if got.ID != created.ID || got.Title != created.Title || got.Author != created.Author ||
		got.Year != created.Year || got.ISBN != created.ISBN {
		t.Fatalf("retrieved book mismatch: %+v", got)
	}
}

// TestValidationErrors checks that missing required fields are rejected.
func TestValidationErrors(t *testing.T) {
	srv, _ := newTestServer(t)

	for _, tc := range []struct {
		name string
		body map[string]any
	}{
		{"missing title", map[string]any{"author": "Someone", "year": 2020}},
		{"missing author", map[string]any{"title": "Something", "year": 2020}},
		{"empty body", map[string]any{}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			resp := doJSON(t, http.MethodPost, srv.URL+"/books", tc.body)
			defer resp.Body.Close()
			if resp.StatusCode != http.StatusBadRequest {
				t.Fatalf("expected 400, got %d", resp.StatusCode)
			}
		})
	}
}

// TestListAndFilter verifies listing returns all books and that the author
// query parameter filters the results.
func TestListAndFilter(t *testing.T) {
	srv, _ := newTestServer(t)

	mustCreateBook(t, srv, model.BookInput{Title: "Book A", Author: "Alice", Year: 2001})
	mustCreateBook(t, srv, model.BookInput{Title: "Book B", Author: "Bob", Year: 2002})
	mustCreateBook(t, srv, model.BookInput{Title: "Book C", Author: "Alice", Year: 2003})

	// List all
	resp := doJSON(t, http.MethodGet, srv.URL+"/books", nil)
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}
	var all []model.Book
	if err := json.NewDecoder(resp.Body).Decode(&all); err != nil {
		t.Fatalf("decode body: %v", err)
	}
	if len(all) != 3 {
		t.Fatalf("expected 3 books, got %d", len(all))
	}

	// Filter by author
	resp = doJSON(t, http.MethodGet, srv.URL+"/books?author=Alice", nil)
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}
	var filtered []model.Book
	if err := json.NewDecoder(resp.Body).Decode(&filtered); err != nil {
		t.Fatalf("decode body: %v", err)
	}
	if len(filtered) != 2 {
		t.Fatalf("expected 2 books for Alice, got %d", len(filtered))
	}
	for _, b := range filtered {
		if b.Author != "Alice" {
			t.Fatalf("unexpected author: %q", b.Author)
		}
	}
}

// TestUpdateBook verifies an existing book can be updated.
func TestUpdateBook(t *testing.T) {
	srv, _ := newTestServer(t)

	created := mustCreateBook(t, srv, model.BookInput{
		Title:  "Old Title",
		Author: "Old Author",
		Year:   2010,
		ISBN:   "old-isbn",
	})

	resp := doJSON(t, http.MethodPut, srv.URL+"/books/"+strconv.Itoa(created.ID), model.BookInput{
		Title:  "New Title",
		Author: "New Author",
		Year:   2020,
		ISBN:   "new-isbn",
	})
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}
	var updated model.Book
	if err := json.NewDecoder(resp.Body).Decode(&updated); err != nil {
		t.Fatalf("decode body: %v", err)
	}
	if updated.Title != "New Title" || updated.Author != "New Author" ||
		updated.Year != 2020 || updated.ISBN != "new-isbn" {
		t.Fatalf("update mismatch: %+v", updated)
	}

	// Updating a non-existent book returns 404.
	resp2 := doJSON(t, http.MethodPut, srv.URL+"/books/9999", model.BookInput{
		Title: "X", Author: "Y", Year: 1, ISBN: "",
	})
	defer resp2.Body.Close()
	if resp2.StatusCode != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", resp2.StatusCode)
	}
}

// TestDeleteBook verifies deletion and that a second delete returns 404.
func TestDeleteBook(t *testing.T) {
	srv, _ := newTestServer(t)

	created := mustCreateBook(t, srv, model.BookInput{
		Title:  "To Delete",
		Author: "Author",
		Year:   2018,
		ISBN:   "isbn-1",
	})

	resp := doJSON(t, http.MethodDelete, srv.URL+"/books/"+strconv.Itoa(created.ID), nil)
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusNoContent {
		t.Fatalf("expected 204, got %d", resp.StatusCode)
	}

	// GET after delete should 404.
	resp = doJSON(t, http.MethodGet, srv.URL+"/books/"+strconv.Itoa(created.ID), nil)
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("expected 404 after delete, got %d", resp.StatusCode)
	}

	// Deleting again should 404.
	resp = doJSON(t, http.MethodDelete, srv.URL+"/books/"+strconv.Itoa(created.ID), nil)
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("expected 404 on second delete, got %d", resp.StatusCode)
	}
}

// TestGetMissingBook verifies that an unknown id returns 404.
func TestGetMissingBook(t *testing.T) {
	srv, _ := newTestServer(t)
	resp := doJSON(t, http.MethodGet, srv.URL+"/books/9999", nil)
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", resp.StatusCode)
	}
}

// TestHealth verifies the health check endpoint.
func TestHealth(t *testing.T) {
	srv, _ := newTestServer(t)
	resp := doJSON(t, http.MethodGet, srv.URL+"/health", nil)
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}
	var body map[string]string
	if err := json.NewDecoder(resp.Body).Decode(&body); err != nil {
		t.Fatalf("decode body: %v", err)
	}
	if body["status"] != "ok" {
		t.Fatalf("expected status ok, got %q", body["status"])
	}
}

// TestInvalidID checks that a non-numeric id is rejected.
func TestInvalidID(t *testing.T) {
	srv, _ := newTestServer(t)
	resp := doJSON(t, http.MethodGet, srv.URL+"/books/abc", nil)
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", resp.StatusCode)
	}
}
