package handlers

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"bookapi/internal/database"
)

func setupTestRouter(t *testing.T) (*gin.Engine, *database.DB) {
	gin.SetMode(gin.TestMode)

	db, err := database.NewDB(":memory:")
	require.NoError(t, err)

	h := NewHandlers(db)

	r := gin.Default()
	r.GET("/health", h.HealthCheck)

	books := r.Group("/books")
	{
		books.POST("", h.CreateBook)
		books.GET("", h.ListBooks)
		books.GET("/:id", h.GetBook)
		books.PUT("/:id", h.UpdateBook)
		books.DELETE("/:id", h.DeleteBook)
	}

	return r, db
}

func TestHealthCheck(t *testing.T) {
	r, _ := setupTestRouter(t)

	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]string
	json.Unmarshal(w.Body.Bytes(), &resp)
	assert.Equal(t, "healthy", resp["status"])
}

func TestCreateBook(t *testing.T) {
	r, _ := setupTestRouter(t)

	// Test valid book creation
	book := map[string]interface{}{
		"title":          "The Go Programming Language",
		"author":         "Alan Donovan",
		"published_year": 2015,
	}
	body, _ := json.Marshal(book)

	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusCreated, w.Code)

	var created database.Book
	json.Unmarshal(w.Body.Bytes(), &created)
	assert.Equal(t, "The Go Programming Language", created.Title)
	assert.Equal(t, "Alan Donovan", created.Author)
	assert.Equal(t, 2015, created.Published)
	assert.Greater(t, created.ID, int64(0))
}

func TestCreateBookValidation(t *testing.T) {
	r, _ := setupTestRouter(t)

	// Test missing title
	book := map[string]interface{}{"author": "Author"}
	body, _ := json.Marshal(book)

	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusBadRequest, w.Code)
	var resp map[string]string
	json.Unmarshal(w.Body.Bytes(), &resp)
	assert.Contains(t, resp["error"], "title is required")

	// Test missing author
	book = map[string]interface{}{"title": "Title"}
	body, _ = json.Marshal(book)

	w = httptest.NewRecorder()
	req = httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusBadRequest, w.Code)
	json.Unmarshal(w.Body.Bytes(), &resp)
	assert.Contains(t, resp["error"], "author is required")
}

func TestGetBook(t *testing.T) {
	r, _ := setupTestRouter(t)

	// Create a book first
	createBody, _ := json.Marshal(map[string]interface{}{
		"title":  "Test Book",
		"author": "Test Author",
	})
	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(createBody))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	var created database.Book
	json.Unmarshal(w.Body.Bytes(), &created)

	// Get the book
	w = httptest.NewRecorder()
	req = httptest.NewRequest(http.MethodGet, "/books/"+strconv.FormatInt(created.ID, 10), nil)
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var book database.Book
	json.Unmarshal(w.Body.Bytes(), &book)
	assert.Equal(t, created.ID, book.ID)
	assert.Equal(t, "Test Book", book.Title)
	assert.Equal(t, "Test Author", book.Author)
}

func TestGetBookNotFound(t *testing.T) {
	r, _ := setupTestRouter(t)

	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/books/999", nil)
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusNotFound, w.Code)
	var resp map[string]string
	json.Unmarshal(w.Body.Bytes(), &resp)
	assert.Equal(t, "book not found", resp["error"])
}

func TestListBooks(t *testing.T) {
	r, _ := setupTestRouter(t)

	// Create a few books
	books := []map[string]interface{}{
		{"title": "Book 1", "author": "Author A"},
		{"title": "Book 2", "author": "Author B"},
		{"title": "Book 3", "author": "Author A"},
	}

	for _, b := range books {
		body, _ := json.Marshal(b)
		w := httptest.NewRecorder()
		req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(body))
		req.Header.Set("Content-Type", "application/json")
		r.ServeHTTP(w, req)
		assert.Equal(t, http.StatusCreated, w.Code)
	}

	// List all books
	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/books", nil)
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)
	booksList := resp["books"].([]interface{})
	assert.GreaterOrEqual(t, len(booksList), 3)
}

func TestListBooksWithAuthorFilter(t *testing.T) {
	r, _ := setupTestRouter(t)

	// Create books with different authors
	testBooks := []map[string]interface{}{
		{"title": "Book A1", "author": "Author A"},
		{"title": "Book A2", "author": "Author A"},
		{"title": "Book B1", "author": "Author B"},
	}

	for _, b := range testBooks {
		body, _ := json.Marshal(b)
		w := httptest.NewRecorder()
		req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(body))
		req.Header.Set("Content-Type", "application/json")
		r.ServeHTTP(w, req)
		assert.Equal(t, http.StatusCreated, w.Code)
	}

	// Filter by author A
	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/books?author=Author%20A", nil)
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)
	booksList := resp["books"].([]interface{})
	assert.Equal(t, 2, len(booksList))
}

func TestUpdateBook(t *testing.T) {
	r, _ := setupTestRouter(t)

	// Create a book
	createBody, _ := json.Marshal(map[string]interface{}{
		"title":  "Original Title",
		"author": "Original Author",
	})
	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(createBody))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	var created database.Book
	json.Unmarshal(w.Body.Bytes(), &created)

	// Update the book
	updateBody, _ := json.Marshal(map[string]interface{}{
		"title":  "Updated Title",
		"author": "Updated Author",
	})
	w = httptest.NewRecorder()
	req = httptest.NewRequest(http.MethodPut, "/books/"+strconv.FormatInt(created.ID, 10), bytes.NewBuffer(updateBody))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var updated database.Book
	json.Unmarshal(w.Body.Bytes(), &updated)
	assert.Equal(t, "Updated Title", updated.Title)
	assert.Equal(t, "Updated Author", updated.Author)
	assert.Equal(t, created.ID, updated.ID)
}

func TestUpdateBookNotFound(t *testing.T) {
	r, _ := setupTestRouter(t)

	updateBody, _ := json.Marshal(map[string]interface{}{
		"title":  "Updated Title",
		"author": "Updated Author",
	})
	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPut, "/books/999", bytes.NewBuffer(updateBody))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusNotFound, w.Code)
}

func TestDeleteBook(t *testing.T) {
	r, _ := setupTestRouter(t)

	// Create a book
	createBody, _ := json.Marshal(map[string]interface{}{
		"title":  "To Delete",
		"author": "Author",
	})
	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(createBody))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	var created database.Book
	json.Unmarshal(w.Body.Bytes(), &created)

	// Delete the book
	w = httptest.NewRecorder()
	req = httptest.NewRequest(http.MethodDelete, "/books/"+strconv.FormatInt(created.ID, 10), nil)
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusNoContent, w.Code)

	// Verify it's gone
	w = httptest.NewRecorder()
	req = httptest.NewRequest(http.MethodGet, "/books/"+strconv.FormatInt(created.ID, 10), nil)
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusNotFound, w.Code)
}

func TestDeleteBookNotFound(t *testing.T) {
	r, _ := setupTestRouter(t)

	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodDelete, "/books/999", nil)
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusNotFound, w.Code)
}
