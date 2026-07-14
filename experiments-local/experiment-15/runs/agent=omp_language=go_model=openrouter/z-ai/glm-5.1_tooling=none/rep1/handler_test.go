package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"
)

func setupTestAPI(t *testing.T) *API {
	t.Helper()
	repo, err := NewBookRepo(":memory:")
	if err != nil {
		t.Fatalf("setup db: %v", err)
	}
	t.Cleanup(func() { repo.Close() })
	return NewAPI(repo)
}

func postBook(t *testing.T, api *API, body any) *httptest.ResponseRecorder {
	t.Helper()
	b, _ := json.Marshal(body)
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(b))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	api.ServeHTTP(w, req)
	return w
}

// --- Test 1: Create and retrieve a book ---

func TestCreateAndGetBook(t *testing.T) {
	api := setupTestAPI(t)

	// Create
	w := postBook(t, api, BookInput{Title: "The Go Programming Language", Author: "Donovan & Kernighan", Year: 2015, ISBN: "978-0134190440"})
	if w.Code != http.StatusCreated {
		t.Fatalf("create status: got %d, want %d; body: %s", w.Code, http.StatusCreated, w.Body.String())
	}
	var created Book
	json.Unmarshal(w.Body.Bytes(), &created)
	if created.ID == 0 {
		t.Fatal("expected non-zero ID")
	}
	if created.Title != "The Go Programming Language" {
		t.Fatalf("title: got %q", created.Title)
	}

	// Get by ID
	req := httptest.NewRequest(http.MethodGet, "/books/"+itoa(created.ID), nil)
	w = httptest.NewRecorder()
	api.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("get status: got %d", w.Code)
	}
	var got Book
	json.Unmarshal(w.Body.Bytes(), &got)
	if got.Title != created.Title {
		t.Fatalf("roundtrip title: got %q, want %q", got.Title, created.Title)
	}
}

// --- Test 2: Validation rejects missing title/author ---

func TestCreateBookValidation(t *testing.T) {
	api := setupTestAPI(t)

	w := postBook(t, api, BookInput{Year: 2020})
	if w.Code != http.StatusUnprocessableEntity {
		t.Fatalf("validation status: got %d, want %d", w.Code, http.StatusUnprocessableEntity)
	}
	var resp map[string]map[string]string
	json.Unmarshal(w.Body.Bytes(), &resp)
	errs := resp["errors"]
	if errs["title"] == "" || errs["author"] == "" {
		t.Fatalf("expected both validation errors, got: %v", errs)
	}
}

// --- Test 3: List with author filter ---

func TestListBooksWithFilter(t *testing.T) {
	api := setupTestAPI(t)

	postBook(t, api, BookInput{Title: "Book A", Author: "Alice"})
	postBook(t, api, BookInput{Title: "Book B", Author: "Bob"})
	postBook(t, api, BookInput{Title: "Book C", Author: "Alice"})

	// No filter — 3 books
	req := httptest.NewRequest(http.MethodGet, "/books", nil)
	w := httptest.NewRecorder()
	api.ServeHTTP(w, req)
	var all []Book
	json.Unmarshal(w.Body.Bytes(), &all)
	if len(all) != 3 {
		t.Fatalf("unfiltered count: got %d, want 3", len(all))
	}

	// Filter by author=Alice — 2 books
	req = httptest.NewRequest(http.MethodGet, "/books?author=Alice", nil)
	w = httptest.NewRecorder()
	api.ServeHTTP(w, req)
	var filtered []Book
	json.Unmarshal(w.Body.Bytes(), &filtered)
	if len(filtered) != 2 {
		t.Fatalf("filtered count: got %d, want 2", len(filtered))
	}
	for _, b := range filtered {
		if b.Author != "Alice" {
			t.Fatalf("expected Alice, got %q", b.Author)
		}
	}
}

// --- Test 4: Update and delete ---

func TestUpdateAndDeleteBook(t *testing.T) {
	api := setupTestAPI(t)

	w := postBook(t, api, BookInput{Title: "Original", Author: "Author"})
	var created Book
	json.Unmarshal(w.Body.Bytes(), &created)

	// Update
	b, _ := json.Marshal(BookInput{Title: "Updated", Author: "NewAuthor", Year: 2024})
	req := httptest.NewRequest(http.MethodPut, "/books/"+itoa(created.ID), bytes.NewReader(b))
	req.Header.Set("Content-Type", "application/json")
	w = httptest.NewRecorder()
	api.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("update status: got %d", w.Code)
	}
	var updated Book
	json.Unmarshal(w.Body.Bytes(), &updated)
	if updated.Title != "Updated" || updated.Author != "NewAuthor" {
		t.Fatalf("updated fields: %+v", updated)
	}

	// Delete
	req = httptest.NewRequest(http.MethodDelete, "/books/"+itoa(created.ID), nil)
	w = httptest.NewRecorder()
	api.ServeHTTP(w, req)
	if w.Code != http.StatusNoContent {
		t.Fatalf("delete status: got %d, want %d", w.Code, http.StatusNoContent)
	}

	// Get after delete — 404
	req = httptest.NewRequest(http.MethodGet, "/books/"+itoa(created.ID), nil)
	w = httptest.NewRecorder()
	api.ServeHTTP(w, req)
	if w.Code != http.StatusNotFound {
		t.Fatalf("after delete status: got %d, want %d", w.Code, http.StatusNotFound)
	}
}

// --- Test 5: Health check ---

func TestHealthCheck(t *testing.T) {
	api := setupTestAPI(t)
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	w := httptest.NewRecorder()
	api.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("health status: got %d", w.Code)
	}
	var resp map[string]string
	json.Unmarshal(w.Body.Bytes(), &resp)
	if resp["status"] != "ok" {
		t.Fatalf("health body: %v", resp)
	}
}

// --- Test 6: GET /books/{id} with non-existent ID returns 404 ---

func TestGetBookNotFound(t *testing.T) {
	api := setupTestAPI(t)
	req := httptest.NewRequest(http.MethodGet, "/books/9999", nil)
	w := httptest.NewRecorder()
	api.ServeHTTP(w, req)
	if w.Code != http.StatusNotFound {
		t.Fatalf("not found status: got %d, want %d", w.Code, http.StatusNotFound)
	}
}

func itoa(n int64) string {
	return strconv.FormatInt(n, 10)
}
