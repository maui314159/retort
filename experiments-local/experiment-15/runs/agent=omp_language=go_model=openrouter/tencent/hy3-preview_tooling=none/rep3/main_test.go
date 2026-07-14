package main

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strconv"
	"testing"
	"time"
)

// setupTestDB creates a temporary database for testing
func setupTestDB(t *testing.T) *BookStore {
	t.Helper()
	store, err := NewBookStore(":memory:")
	if err != nil {
		t.Fatalf("Failed to create test database: %v", err)
	}
	return store
}

// createTestServer creates a test server with the handler
func createTestServer(store *BookStore) *httptest.Server {
	handler := NewHandler(store)
	mux := http.NewServeMux()
	handler.RegisterRoutes(mux)
	return httptest.NewServer(mux)
}

// Test 1: Health Check Endpoint
func TestHealthCheck(t *testing.T) {
	store := setupTestDB(t)
	defer store.Close()

	server := createTestServer(store)
	defer server.Close()

	resp, err := http.Get(server.URL + "/health")
	if err != nil {
		t.Fatalf("Failed to make request: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected status 200, got %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		t.Fatalf("Failed to read response body: %v", err)
	}

	var health HealthResponse
	if err := json.Unmarshal(body, &health); err != nil {
		t.Fatalf("Failed to parse JSON: %v", err)
	}

	if health.Status != "healthy" {
		t.Errorf("Expected status 'healthy', got '%s'", health.Status)
	}

	// Verify time is in RFC3339 format
	if _, err := time.Parse(time.RFC3339, health.Time); err != nil {
		t.Errorf("Time is not in RFC3339 format: %v", err)
	}
}

// Test 2: Create and Get Book
func TestCreateAndGetBook(t *testing.T) {
	store := setupTestDB(t)
	defer store.Close()

	server := createTestServer(store)
	defer server.Close()

	// Create a book
	bookReq := CreateBookRequest{
		Title:  "The Go Programming Language",
		Author: "Alan A. A. Donovan",
		Year:   2015,
		ISBN:   "978-0134190440",
	}

	body, err := json.Marshal(bookReq)
	if err != nil {
		t.Fatalf("Failed to marshal request: %v", err)
	}

	resp, err := http.Post(server.URL+"/books", "application/json", bytes.NewBuffer(body))
	if err != nil {
		t.Fatalf("Failed to make request: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusCreated {
		t.Errorf("Expected status 201, got %d", resp.StatusCode)
	}

	var createdBook Book
	if err := json.NewDecoder(resp.Body).Decode(&createdBook); err != nil {
		t.Fatalf("Failed to parse JSON: %v", err)
	}

	if createdBook.ID == 0 {
		t.Error("Expected book ID to be set")
	}
	if createdBook.Title != bookReq.Title {
		t.Errorf("Expected title '%s', got '%s'", bookReq.Title, createdBook.Title)
	}
	if createdBook.Author != bookReq.Author {
		t.Errorf("Expected author '%s', got '%s'", bookReq.Author, createdBook.Author)
	}

	// Get the book by ID
	getResp, err := http.Get(server.URL + "/books/" + strconv.FormatInt(createdBook.ID, 10))
	if err != nil {
		t.Fatalf("Failed to make request: %v", err)
	}
	defer getResp.Body.Close()

	if getResp.StatusCode != http.StatusOK {
		t.Errorf("Expected status 200, got %d", getResp.StatusCode)
	}

	var fetchedBook Book
	if err := json.NewDecoder(getResp.Body).Decode(&fetchedBook); err != nil {
		t.Fatalf("Failed to parse JSON: %v", err)
	}

	if fetchedBook.ID != createdBook.ID {
		t.Errorf("Expected ID %d, got %d", createdBook.ID, fetchedBook.ID)
	}
}

// Test 3: List Books with Filter
func TestListBooksWithFilter(t *testing.T) {
	store := setupTestDB(t)
	defer store.Close()

	server := createTestServer(store)
	defer server.Close()

	// Create multiple books
	books := []CreateBookRequest{
		{Title: "Book 1", Author: "Author A"},
		{Title: "Book 2", Author: "Author B"},
		{Title: "Book 3", Author: "Author A"},
	}

	for _, book := range books {
		body, _ := json.Marshal(book)
		resp, err := http.Post(server.URL+"/books", "application/json", bytes.NewBuffer(body))
		if err != nil {
			t.Fatalf("Failed to create book: %v", err)
		}
		resp.Body.Close()
	}

	// List all books
	resp, err := http.Get(server.URL + "/books")
	if err != nil {
		t.Fatalf("Failed to make request: %v", err)
	}

	respBody, _ := io.ReadAll(resp.Body)
	resp.Body.Close()

	var allBooks []Book
	if err := json.Unmarshal(respBody, &allBooks); err != nil {
		t.Fatalf("Failed to parse JSON: %v", err)
	}

	if len(allBooks) != 3 {
		t.Errorf("Expected 3 books, got %d", len(allBooks))
	}

	// Filter by author (URL-encode the parameter)
	authorFilter := url.QueryEscape("Author A")
	resp2, err := http.Get(server.URL + "/books?author=" + authorFilter)
	if err != nil {
		t.Fatalf("Failed to make request: %v", err)
	}
	defer resp2.Body.Close()

	var filteredBooks []Book
	if err := json.NewDecoder(resp2.Body).Decode(&filteredBooks); err != nil {
		t.Fatalf("Failed to parse JSON: %v", err)
	}

	if len(filteredBooks) != 2 {
		t.Errorf("Expected 2 books, got %d", len(filteredBooks))
	}

	for _, book := range filteredBooks {
		if book.Author != "Author A" {
			t.Errorf("Expected author 'Author A', got '%s'", book.Author)
		}
	}
}

// Test 4: Update Book
func TestUpdateBook(t *testing.T) {
	store := setupTestDB(t)
	defer store.Close()

	server := createTestServer(store)
	defer server.Close()

	// Create a book
	bookReq := CreateBookRequest{
		Title:  "Original Title",
		Author: "Original Author",
	}

	body, _ := json.Marshal(bookReq)
	resp, err := http.Post(server.URL+"/books", "application/json", bytes.NewBuffer(body))
	if err != nil {
		t.Fatalf("Failed to create book: %v", err)
	}

	var createdBook Book
	json.NewDecoder(resp.Body).Decode(&createdBook)
	resp.Body.Close()

	// Update the book
	newTitle := "Updated Title"
	newYear := 2023
	updateReq := UpdateBookRequest{
		Title: &newTitle,
		Year:  &newYear,
	}

	body, _ = json.Marshal(updateReq)
	req, _ := http.NewRequest(http.MethodPut, server.URL+"/books/"+strconv.FormatInt(createdBook.ID, 10), bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{}
	updateResp, err := client.Do(req)
	if err != nil {
		t.Fatalf("Failed to make request: %v", err)
	}
	defer updateResp.Body.Close()

	if updateResp.StatusCode != http.StatusOK {
		t.Errorf("Expected status 200, got %d", updateResp.StatusCode)
	}

	var updatedBook Book
	json.NewDecoder(updateResp.Body).Decode(&updatedBook)

	if updatedBook.Title != newTitle {
		t.Errorf("Expected title '%s', got '%s'", newTitle, updatedBook.Title)
	}
	if updatedBook.Year != newYear {
		t.Errorf("Expected year %d, got %d", newYear, updatedBook.Year)
	}
	// Author should remain unchanged
	if updatedBook.Author != bookReq.Author {
		t.Errorf("Expected author '%s', got '%s'", bookReq.Author, updatedBook.Author)
	}
}

// Test 5: Delete Book
func TestDeleteBook(t *testing.T) {
	store := setupTestDB(t)
	defer store.Close()

	server := createTestServer(store)
	defer server.Close()

	// Create a book
	bookReq := CreateBookRequest{
		Title:  "Book to Delete",
		Author: "Author",
	}

	body, _ := json.Marshal(bookReq)
	resp, err := http.Post(server.URL+"/books", "application/json", bytes.NewBuffer(body))
	if err != nil {
		t.Fatalf("Failed to create book: %v", err)
	}

	var createdBook Book
	json.NewDecoder(resp.Body).Decode(&createdBook)
	resp.Body.Close()

	// Delete the book
	req, _ := http.NewRequest(http.MethodDelete, server.URL+"/books/"+strconv.FormatInt(createdBook.ID, 10), nil)
	client := &http.Client{}
	delResp, err := client.Do(req)
	if err != nil {
		t.Fatalf("Failed to make request: %v", err)
	}
	defer delResp.Body.Close()

	if delResp.StatusCode != http.StatusNoContent {
		t.Errorf("Expected status 204, got %d", delResp.StatusCode)
	}

	// Try to get the deleted book
	getResp, err := http.Get(server.URL + "/books/" + strconv.FormatInt(createdBook.ID, 10))
	if err != nil {
		t.Fatalf("Failed to make request: %v", err)
	}
	defer getResp.Body.Close()

	if getResp.StatusCode != http.StatusNotFound {
		t.Errorf("Expected status 404, got %d", getResp.StatusCode)
	}
}

// Test 6: Input Validation
func TestInputValidation(t *testing.T) {
	store := setupTestDB(t)
	defer store.Close()

	server := createTestServer(store)
	defer server.Close()

	// Test missing title
	bookReq := CreateBookRequest{
		Author: "Author",
	}

	body, _ := json.Marshal(bookReq)
	resp, err := http.Post(server.URL+"/books", "application/json", bytes.NewBuffer(body))
	if err != nil {
		t.Fatalf("Failed to make request: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("Expected status 400 for missing title, got %d", resp.StatusCode)
	}

	// Test missing author
	bookReq = CreateBookRequest{
		Title: "Title",
	}

	body, _ = json.Marshal(bookReq)
	resp, err = http.Post(server.URL+"/books", "application/json", bytes.NewBuffer(body))
	if err != nil {
		t.Fatalf("Failed to make request: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("Expected status 400 for missing author, got %d", resp.StatusCode)
	}
}

// Test 7: Book Not Found
func TestBookNotFound(t *testing.T) {
	store := setupTestDB(t)
	defer store.Close()

	server := createTestServer(store)
	defer server.Close()

	// Try to get non-existent book
	resp, err := http.Get(server.URL + "/books/999")
	if err != nil {
		t.Fatalf("Failed to make request: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("Expected status 404, got %d", resp.StatusCode)
	}
}
