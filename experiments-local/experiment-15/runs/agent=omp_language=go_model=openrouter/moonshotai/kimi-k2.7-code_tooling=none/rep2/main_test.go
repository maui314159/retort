package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"
)

func setupTestServer(t *testing.T) *Server {
	t.Helper()
	db, err := openDB(":memory:")
	if err != nil {
		t.Fatalf("failed to open test database: %v", err)
	}
	t.Cleanup(func() { db.Close() })
	return &Server{db: db}
}

func TestHealthEndpoint(t *testing.T) {
	srv := setupTestServer(t)
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	rr := httptest.NewRecorder()

	srv.healthHandler(rr, req)

	if rr.Code != http.StatusOK {
		t.Fatalf("expected status %d, got %d", http.StatusOK, rr.Code)
	}
	var body map[string]string
	if err := json.Unmarshal(rr.Body.Bytes(), &body); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}
	if body["status"] != "ok" {
		t.Fatalf("expected status ok, got %q", body["status"])
	}
}

func TestCreateAndGetBook(t *testing.T) {
	srv := setupTestServer(t)
	router := srv.routes()

	payload := map[string]any{
		"title":  "The Go Programming Language",
		"author": "Alan A. A. Donovan",
		"year":   2015,
		"isbn":   "978-0134190440",
	}
	body, _ := json.Marshal(payload)
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()
	router.ServeHTTP(rr, req)

	if rr.Code != http.StatusCreated {
		t.Fatalf("expected status %d, got %d: %s", http.StatusCreated, rr.Code, rr.Body.String())
	}

	var created Book
	if err := json.Unmarshal(rr.Body.Bytes(), &created); err != nil {
		t.Fatalf("failed to decode created book: %v", err)
	}
	if created.ID == 0 {
		t.Fatalf("expected non-zero book id")
	}
	if created.Title != payload["title"] || created.Author != payload["author"] {
		t.Fatalf("created book mismatch: got %+v", created)
	}

	req = httptest.NewRequest(http.MethodGet, fmt.Sprintf("/books/%d", created.ID), nil)
	rr = httptest.NewRecorder()
	router.ServeHTTP(rr, req)

	if rr.Code != http.StatusOK {
		t.Fatalf("expected status %d, got %d: %s", http.StatusOK, rr.Code, rr.Body.String())
	}

	var fetched Book
	if err := json.Unmarshal(rr.Body.Bytes(), &fetched); err != nil {
		t.Fatalf("failed to decode fetched book: %v", err)
	}
	if fetched.ID != created.ID || fetched.Title != created.Title {
		t.Fatalf("fetched book mismatch: got %+v, want %+v", fetched, created)
	}
}

func TestCreateBookValidation(t *testing.T) {
	srv := setupTestServer(t)
	router := srv.routes()

	tests := []struct {
		name    string
		payload map[string]any
	}{
		{"missing title", map[string]any{"author": "Author", "year": 2020}},
		{"empty title", map[string]any{"title": "   ", "author": "Author", "year": 2020}},
		{"missing author", map[string]any{"title": "Title", "year": 2020}},
		{"empty author", map[string]any{"title": "Title", "author": "   ", "year": 2020}},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			body, _ := json.Marshal(tt.payload)
			req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
			req.Header.Set("Content-Type", "application/json")
			rr := httptest.NewRecorder()
			router.ServeHTTP(rr, req)

			if rr.Code != http.StatusBadRequest {
				t.Fatalf("expected status %d, got %d: %s", http.StatusBadRequest, rr.Code, rr.Body.String())
			}
		})
	}
}

func TestListBooksWithAuthorFilter(t *testing.T) {
	srv := setupTestServer(t)
	router := srv.routes()

	books := []map[string]any{
		{"title": "Book One", "author": "Author A", "year": 2020, "isbn": "111"},
		{"title": "Book Two", "author": "Author B", "year": 2021, "isbn": "222"},
		{"title": "Book Three", "author": "Author A", "year": 2022, "isbn": "333"},
	}
	for _, b := range books {
		body, _ := json.Marshal(b)
		req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
		req.Header.Set("Content-Type", "application/json")
		rr := httptest.NewRecorder()
		router.ServeHTTP(rr, req)
		if rr.Code != http.StatusCreated {
			t.Fatalf("failed to seed book: %s", rr.Body.String())
		}
	}

	req := httptest.NewRequest(http.MethodGet, "/books?author=Author+A", nil)
	rr := httptest.NewRecorder()
	router.ServeHTTP(rr, req)

	if rr.Code != http.StatusOK {
		t.Fatalf("expected status %d, got %d: %s", http.StatusOK, rr.Code, rr.Body.String())
	}

	var result []Book
	if err := json.Unmarshal(rr.Body.Bytes(), &result); err != nil {
		t.Fatalf("failed to decode books: %v", err)
	}
	if len(result) != 2 {
		t.Fatalf("expected 2 books from Author A, got %d", len(result))
	}
	for _, b := range result {
		if b.Author != "Author A" {
			t.Fatalf("expected author Author A, got %s", b.Author)
		}
	}
}

func TestUpdateAndDeleteBook(t *testing.T) {
	srv := setupTestServer(t)
	router := srv.routes()

	body, _ := json.Marshal(map[string]any{"title": "Original", "author": "Original Author", "year": 2020})
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()
	router.ServeHTTP(rr, req)

	if rr.Code != http.StatusCreated {
		t.Fatalf("failed to create book: %s", rr.Body.String())
	}
	var created Book
	json.Unmarshal(rr.Body.Bytes(), &created)

	update := map[string]any{"title": "Updated", "author": "Updated Author", "year": 2021, "isbn": "999"}
	body, _ = json.Marshal(update)
	req = httptest.NewRequest(http.MethodPut, fmt.Sprintf("/books/%d", created.ID), bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	rr = httptest.NewRecorder()
	router.ServeHTTP(rr, req)

	if rr.Code != http.StatusOK {
		t.Fatalf("expected status %d, got %d: %s", http.StatusOK, rr.Code, rr.Body.String())
	}
	var updated Book
	json.Unmarshal(rr.Body.Bytes(), &updated)
	if updated.Title != "Updated" || updated.Author != "Updated Author" {
		t.Fatalf("update mismatch: got %+v", updated)
	}

	req = httptest.NewRequest(http.MethodDelete, fmt.Sprintf("/books/%d", created.ID), nil)
	rr = httptest.NewRecorder()
	router.ServeHTTP(rr, req)
	if rr.Code != http.StatusNoContent {
		t.Fatalf("expected status %d, got %d", http.StatusNoContent, rr.Code)
	}

	req = httptest.NewRequest(http.MethodGet, fmt.Sprintf("/books/%d", created.ID), nil)
	rr = httptest.NewRecorder()
	router.ServeHTTP(rr, req)
	if rr.Code != http.StatusNotFound {
		t.Fatalf("expected status %d after delete, got %d", http.StatusNotFound, rr.Code)
	}
}
