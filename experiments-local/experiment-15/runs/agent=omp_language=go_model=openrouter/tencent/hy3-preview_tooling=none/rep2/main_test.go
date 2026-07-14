package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"
)

func setupTestServer() (*http.ServeMux, *Storage) {
	storage, _ := NewStorage(":memory:")
	mux := http.NewServeMux()
	handler := NewHandler(storage)

	mux.HandleFunc("/books", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodPost:
			handler.CreateBook(w, r)
		case http.MethodGet:
			handler.GetBooks(w, r)
		default:
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	})

	mux.HandleFunc("/books/", func(w http.ResponseWriter, r *http.Request) {
		path := r.URL.Path
		if path == "/books/" {
			http.Error(w, "Not found", http.StatusNotFound)
			return
		}

		switch r.Method {
		case http.MethodGet:
			handler.GetBook(w, r)
		case http.MethodPut:
			handler.UpdateBook(w, r)
		case http.MethodDelete:
			handler.DeleteBook(w, r)
		default:
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	})

	mux.HandleFunc("/health", handler.HealthCheck)

	return mux, storage
}

func TestHealthCheck(t *testing.T) {
	mux, _ := setupTestServer()
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	w := httptest.NewRecorder()

	mux.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var response HealthResponse
	if err := json.NewDecoder(w.Body).Decode(&response); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if response.Status != "healthy" {
		t.Errorf("Expected status 'healthy', got '%s'", response.Status)
	}
}

func TestCreateAndGetBook(t *testing.T) {
	mux, _ := setupTestServer()

	createReq := CreateBookRequest{
		Title:  "The Go Programming Language",
		Author: "Alan Donovan",
		Year:   2015,
		ISBN:   "978-0134190440",
	}
	body, _ := json.Marshal(createReq)

	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	mux.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("Expected status 201, got %d", w.Code)
	}

	var createdBook Book
	if err := json.NewDecoder(w.Body).Decode(&createdBook); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if createdBook.ID == 0 {
		t.Error("Expected book ID to be set")
	}
	if createdBook.Title != "The Go Programming Language" {
		t.Errorf("Expected title 'The Go Programming Language', got '%s'", createdBook.Title)
	}

	getReq := httptest.NewRequest(http.MethodGet, "/books/"+strconv.FormatInt(createdBook.ID, 10), nil)
	getW := httptest.NewRecorder()
	mux.ServeHTTP(getW, getReq)

	if getW.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", getW.Code)
	}

	var fetchedBook Book
	if err := json.NewDecoder(getW.Body).Decode(&fetchedBook); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if fetchedBook.ID != createdBook.ID {
		t.Errorf("Expected ID %d, got %d", createdBook.ID, fetchedBook.ID)
	}
}

func TestListBooksWithFilter(t *testing.T) {
	mux, _ := setupTestServer()

	books := []CreateBookRequest{
		{Title: "Book 1", Author: "Author A"},
		{Title: "Book 2", Author: "Author B"},
		{Title: "Book 3", Author: "Author A"},
	}

	for _, b := range books {
		body, _ := json.Marshal(b)
		req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		mux.ServeHTTP(w, req)
		if w.Code != http.StatusCreated {
			t.Fatalf("Failed to create book: got status %d", w.Code)
		}
	}

	req := httptest.NewRequest(http.MethodGet, "/books?author=Author+A", nil)
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var result []*Book
	if err := json.NewDecoder(w.Body).Decode(&result); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if len(result) != 2 {
		t.Errorf("Expected 2 books, got %d", len(result))
	}
}

func TestUpdateBook(t *testing.T) {
	mux, _ := setupTestServer()

	createReq := CreateBookRequest{
		Title:  "Original Title",
		Author: "Original Author",
		Year:   2020,
	}
	body, _ := json.Marshal(createReq)
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	var createdBook Book
	json.NewDecoder(w.Body).Decode(&createdBook)

	newTitle := "Updated Title"
	updateReq := UpdateBookRequest{
		Title: &newTitle,
	}
	updateBody, _ := json.Marshal(updateReq)

	updateHTTPReq := httptest.NewRequest(http.MethodPut, "/books/"+strconv.FormatInt(createdBook.ID, 10), bytes.NewReader(updateBody))
	updateHTTPReq.Header.Set("Content-Type", "application/json")
	updateW := httptest.NewRecorder()
	mux.ServeHTTP(updateW, updateHTTPReq)

	if updateW.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", updateW.Code)
	}

	var updatedBook Book
	json.NewDecoder(updateW.Body).Decode(&updatedBook)

	if updatedBook.Title != "Updated Title" {
		t.Errorf("Expected title 'Updated Title', got '%s'", updatedBook.Title)
	}
	if updatedBook.Author != "Original Author" {
		t.Errorf("Expected author 'Original Author', got '%s'", updatedBook.Author)
	}
	if updatedBook.Year != 2020 {
		t.Errorf("Expected year 2020, got %d", updatedBook.Year)
	}
}

func TestDeleteBook(t *testing.T) {
	mux, _ := setupTestServer()

	createReq := CreateBookRequest{
		Title:  "To be deleted",
		Author: "Author",
	}
	body, _ := json.Marshal(createReq)
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	var createdBook Book
	json.NewDecoder(w.Body).Decode(&createdBook)

	deleteReq := httptest.NewRequest(http.MethodDelete, "/books/"+strconv.FormatInt(createdBook.ID, 10), nil)
	deleteW := httptest.NewRecorder()
	mux.ServeHTTP(deleteW, deleteReq)

	if deleteW.Code != http.StatusNoContent {
		t.Errorf("Expected status 204, got %d", deleteW.Code)
	}

	getReq := httptest.NewRequest(http.MethodGet, "/books/"+strconv.FormatInt(createdBook.ID, 10), nil)
	getW := httptest.NewRecorder()
	mux.ServeHTTP(getW, getReq)

	if getW.Code != http.StatusNotFound {
		t.Errorf("Expected status 404, got %d", getW.Code)
	}
}

func TestValidationErrors(t *testing.T) {
	mux, _ := setupTestServer()

	tests := []struct {
		name string
		req  CreateBookRequest
	}{
		{"missing title", CreateBookRequest{Author: "Author"}},
		{"missing author", CreateBookRequest{Title: "Title"}},
		{"missing both", CreateBookRequest{}},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			body, _ := json.Marshal(tt.req)
			req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
			req.Header.Set("Content-Type", "application/json")
			w := httptest.NewRecorder()
			mux.ServeHTTP(w, req)

			if w.Code != http.StatusBadRequest {
				t.Errorf("Expected status 400, got %d", w.Code)
			}

			var errResp ErrorResponse
			json.NewDecoder(w.Body).Decode(&errResp)

			if errResp.Error == "" {
				t.Error("Expected error message in response")
			}
		})
	}
}

func TestNotFoundBook(t *testing.T) {
	mux, _ := setupTestServer()

	req := httptest.NewRequest(http.MethodGet, "/books/999", nil)
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status 404, got %d", w.Code)
	}
}
