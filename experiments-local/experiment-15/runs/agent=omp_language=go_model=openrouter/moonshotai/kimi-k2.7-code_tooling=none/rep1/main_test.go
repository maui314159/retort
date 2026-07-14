package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"
)

func setupTestServer(t *testing.T) (*server, *sql.DB) {
	t.Helper()
	db, err := sql.Open("sqlite", ":memory:")
	if err != nil {
		t.Fatalf("open test database: %v", err)
	}
	if err := migrate(db); err != nil {
		t.Fatalf("migrate test database: %v", err)
	}
	return &server{db: db}, db
}

func TestHealthCheck(t *testing.T) {
	srv, db := setupTestServer(t)
	defer db.Close()

	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	rec := httptest.NewRecorder()
	srv.routes().ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected status 200, got %d", rec.Code)
	}
	var body map[string]string
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatalf("decode response: %v", err)
	}
	if body["status"] != "ok" {
		t.Fatalf("expected status ok, got %v", body)
	}
}

func TestCreateBookValidation(t *testing.T) {
	srv, db := setupTestServer(t)
	defer db.Close()

	cases := []struct {
		name   string
		body   string
		status int
	}{
		{"missing title", `{"author":"Orwell","year":1949,"isbn":"978-0451524935"}`, http.StatusBadRequest},
		{"missing author", `{"title":"1984","year":1949,"isbn":"978-0451524935"}`, http.StatusBadRequest},
		{"empty title", `{"title":"   ","author":"Orwell"}`, http.StatusBadRequest},
		{"valid book", `{"title":"1984","author":"George Orwell","year":1949,"isbn":"978-0451524935"}`, http.StatusCreated},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBufferString(tc.body))
			req.Header.Set("Content-Type", "application/json")
			rec := httptest.NewRecorder()
			srv.routes().ServeHTTP(rec, req)

			if rec.Code != tc.status {
				t.Fatalf("expected status %d, got %d: %s", tc.status, rec.Code, rec.Body.String())
			}
		})
	}
}

func TestBookCRUD(t *testing.T) {
	srv, db := setupTestServer(t)
	defer db.Close()

	// Create
	createBody := `{"title":"The Go Programming Language","author":"Alan A. A. Donovan","year":2015,"isbn":"978-0134190440"}`
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBufferString(createBody))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	srv.routes().ServeHTTP(rec, req)

	if rec.Code != http.StatusCreated {
		t.Fatalf("create: expected status 201, got %d: %s", rec.Code, rec.Body.String())
	}
	var created Book
	if err := json.Unmarshal(rec.Body.Bytes(), &created); err != nil {
		t.Fatalf("create: decode response: %v", err)
	}
	if created.ID == 0 {
		t.Fatalf("create: expected assigned id")
	}

	// List
	req = httptest.NewRequest(http.MethodGet, "/books", nil)
	rec = httptest.NewRecorder()
	srv.routes().ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("list: expected status 200, got %d", rec.Code)
	}
	var listed []Book
	if err := json.Unmarshal(rec.Body.Bytes(), &listed); err != nil {
		t.Fatalf("list: decode response: %v", err)
	}
	if len(listed) != 1 || listed[0].ID != created.ID {
		t.Fatalf("list: expected one book with id %d, got %v", created.ID, listed)
	}

	// List with author filter
	req = httptest.NewRequest(http.MethodGet, "/books?author=Alan", nil)
	rec = httptest.NewRecorder()
	srv.routes().ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("list filter: expected status 200, got %d", rec.Code)
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &listed); err != nil {
		t.Fatalf("list filter: decode response: %v", err)
	}
	if len(listed) != 1 {
		t.Fatalf("list filter: expected one match, got %d", len(listed))
	}

	// Get
	req = httptest.NewRequest(http.MethodGet, "/books/"+strconv.FormatInt(created.ID, 10), nil)
	rec = httptest.NewRecorder()
	srv.routes().ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("get: expected status 200, got %d: %s", rec.Code, rec.Body.String())
	}
	var fetched Book
	if err := json.Unmarshal(rec.Body.Bytes(), &fetched); err != nil {
		t.Fatalf("get: decode response: %v", err)
	}
	if fetched.Title != created.Title {
		t.Fatalf("get: title mismatch")
	}

	// Update
	updateBody := `{"title":"The Go Programming Language (Updated)","author":"Alan A. A. Donovan","year":2016,"isbn":"978-0134190440"}`
	req = httptest.NewRequest(http.MethodPut, "/books/"+strconv.FormatInt(created.ID, 10), bytes.NewBufferString(updateBody))
	req.Header.Set("Content-Type", "application/json")
	rec = httptest.NewRecorder()
	srv.routes().ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("update: expected status 200, got %d: %s", rec.Code, rec.Body.String())
	}
	var updated Book
	if err := json.Unmarshal(rec.Body.Bytes(), &updated); err != nil {
		t.Fatalf("update: decode response: %v", err)
	}
	if updated.Year != 2016 {
		t.Fatalf("update: expected year 2016, got %d", updated.Year)
	}

	// Delete
	req = httptest.NewRequest(http.MethodDelete, "/books/"+strconv.FormatInt(created.ID, 10), nil)
	rec = httptest.NewRecorder()
	srv.routes().ServeHTTP(rec, req)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("delete: expected status 204, got %d", rec.Code)
	}
	if rec.Body.Len() != 0 {
		t.Fatalf("delete: expected empty body")
	}

	// Get after delete
	req = httptest.NewRequest(http.MethodGet, "/books/"+strconv.FormatInt(created.ID, 10), nil)
	rec = httptest.NewRecorder()
	srv.routes().ServeHTTP(rec, req)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("get deleted: expected status 404, got %d", rec.Code)
	}
}

func TestNotFound(t *testing.T) {
	srv, db := setupTestServer(t)
	defer db.Close()

	req := httptest.NewRequest(http.MethodGet, "/books/999", nil)
	rec := httptest.NewRecorder()
	srv.routes().ServeHTTP(rec, req)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("expected status 404, got %d", rec.Code)
	}
}

func init() {
	// Silence log output during tests.
	log.SetOutput(io.Discard)
}
