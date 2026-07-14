package handlers

import (
	"bookapi/database"
	"bookapi/repository"
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gorilla/mux"
	"github.com/stretchr/testify/assert"
)

func setupRouter() (*mux.Router, func()) {
	db, err := database.InitDBWithFile(":memory:")
	if err != nil {
		panic(err)
	}
	repo := repository.NewSQLiteBookRepository(db)
	handler := NewHandler(repo)
	r := mux.NewRouter()
	handler.RegisterRoutes(r)
	cleanup := func() {
		db.Close()
	}
	return r, cleanup
}

func TestHealthCheck(t *testing.T) {
	router, cleanup := setupRouter()
	defer cleanup()

	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var response map[string]string
	json.Unmarshal(w.Body.Bytes(), &response)
	assert.Equal(t, "healthy", response["status"])
}

func TestCreateBook(t *testing.T) {
	router, cleanup := setupRouter()
	defer cleanup()

	book := map[string]interface{}{
		"title":  "Test Book",
		"author": "Test Author",
		"year":   2023,
		"isbn":   "1234567890",
	}
	body, _ := json.Marshal(book)

	req := httptest.NewRequest("POST", "/books", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusCreated, w.Code)
	var response map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &response)
	assert.NotNil(t, response["id"])
}

func TestGetBooks(t *testing.T) {
	router, cleanup := setupRouter()
	defer cleanup()

	// Create a book first
	book := map[string]interface{}{
		"title":  "Test Book",
		"author": "Test Author",
		"year":   2023,
		"isbn":   "1234567890",
	}
	body, _ := json.Marshal(book)
	req := httptest.NewRequest("POST", "/books", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	// Get all books
	req = httptest.NewRequest("GET", "/books", nil)
	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var books []map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &books)
	assert.Len(t, books, 1)
	assert.Equal(t, "Test Book", books[0]["title"])
}

func TestGetBookByID(t *testing.T) {
	router, cleanup := setupRouter()
	defer cleanup()

	// Create a book first
	book := map[string]interface{}{
		"title":  "Test Book",
		"author": "Test Author",
		"year":   2023,
		"isbn":   "1234567890",
	}
	body, _ := json.Marshal(book)
	req := httptest.NewRequest("POST", "/books", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	var createResp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &createResp)
	idFloat := createResp["id"].(float64)
	id := int(idFloat)
	t.Logf("Created book ID: %d", id)

	// Get the book by ID
	t.Logf("URL: %s", fmt.Sprintf("/books/%v", id))
	req = httptest.NewRequest("GET", fmt.Sprintf("/books/%v", id), nil)
	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Logf("Response body: %s", w.Body.String())
	}
	assert.Equal(t, http.StatusOK, w.Code)
	var retrievedBook map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &retrievedBook)
	assert.Equal(t, "Test Book", retrievedBook["title"])
}

func TestUpdateBook(t *testing.T) {
	router, cleanup := setupRouter()
	defer cleanup()

	// Create a book first
	book := map[string]interface{}{
		"title":  "Test Book",
		"author": "Test Author",
		"year":   2023,
		"isbn":   "1234567890",
	}
	body, _ := json.Marshal(book)
	req := httptest.NewRequest("POST", "/books", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	var createResp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &createResp)
	idFloat := createResp["id"].(float64)
	id := int(idFloat)

	// Update the book
	updatedBook := map[string]interface{}{
		"title":  "Updated Title",
		"author": "Updated Author",
		"year":   2024,
		"isbn":   "0987654321",
	}
	body, _ = json.Marshal(updatedBook)
	req = httptest.NewRequest("PUT", fmt.Sprintf("/books/%v", id), bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusNoContent, w.Code)

	// Retrieve and verify update
	req = httptest.NewRequest("GET", fmt.Sprintf("/books/%v", id), nil)
	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)
	var retrievedBook map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &retrievedBook)
	assert.Equal(t, "Updated Title", retrievedBook["title"])
	assert.Equal(t, "Updated Author", retrievedBook["author"])
}

func TestDeleteBook(t *testing.T) {
	router, cleanup := setupRouter()
	defer cleanup()

	// Create a book first
	book := map[string]interface{}{
		"title":  "Test Book",
		"author": "Test Author",
		"year":   2023,
		"isbn":   "1234567890",
	}
	body, _ := json.Marshal(book)
	req := httptest.NewRequest("POST", "/books", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	var createResp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &createResp)
	idFloat := createResp["id"].(float64)
	id := int(idFloat)

	// Delete the book
	req = httptest.NewRequest("DELETE", fmt.Sprintf("/books/%v", id), nil)
	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusNoContent, w.Code)

	// Try to retrieve, should get 404
	req = httptest.NewRequest("GET", fmt.Sprintf("/books/%v", id), nil)
	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)
	assert.Equal(t, http.StatusNotFound, w.Code)
}