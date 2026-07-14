package handlers

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"

	"bookapi/models"

	"github.com/go-chi/chi/v5"
	"github.com/stretchr/testify/assert"
)

// MockBookStore implements models.BookStore for testing
type MockBookStore struct {
	books map[string]models.Book
}

func NewMockBookStore() *MockBookStore {
	return &MockBookStore{
		books: make(map[string]models.Book),
	}
}

func (m *MockBookStore) Create(req *models.BookRequest) (*models.Book, error) {
	if req.Title == "" || req.Author == "" {
		return nil, fmt.Errorf("title and author are required")
	}

	book := models.Book{
		ID:     "test-id-123",
		Title:  req.Title,
		Author: req.Author,
		Year:   req.Year,
		ISBN:   req.ISBN,
	}
	m.books[book.ID] = book
	return &book, nil
}

func (m *MockBookStore) GetByID(id string) (*models.Book, error) {
	book, ok := m.books[id]
	if !ok {
		return nil, fmt.Errorf("book not found")
	}
	return &book, nil
}

func (m *MockBookStore) List(authorFilter string) ([]models.Book, error) {
	var books []models.Book
	for _, book := range m.books {
		if authorFilter == "" || book.Author == authorFilter {
			books = append(books, book)
		}
	}
	return books, nil
}

func (m *MockBookStore) Update(id string, req *models.BookRequest) (*models.Book, error) {
	_, ok := m.books[id]
	if !ok {
		return nil, fmt.Errorf("book not found")
	}

	if req.Title == "" || req.Author == "" {
		return nil, fmt.Errorf("title and author are required")
	}

	book := models.Book{
		ID:     id,
		Title:  req.Title,
		Author: req.Author,
		Year:   req.Year,
		ISBN:   req.ISBN,
	}
	m.books[id] = book
	return &book, nil
}

func (m *MockBookStore) Delete(id string) error {
	_, ok := m.books[id]
	if !ok {
		return fmt.Errorf("book not found")
	}
	delete(m.books, id)
	return nil
}

func setupTest() *MockBookStore {
	mockStore := NewMockBookStore()
	TestSetup(mockStore)
	return mockStore
}

func newRequestWithChiContext(method, url, id string, body []byte) *http.Request {
	req := httptest.NewRequest(method, url, bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	
	// Create chi context with URL param
	ctx := chi.NewRouteContext()
	if id != "" {
		ctx.URLParams.Add("id", id)
	}
	req = req.WithContext(context.WithValue(req.Context(), chi.RouteCtxKey, ctx))
	
	return req
}

func TestHealthCheck(t *testing.T) {
	setupTest()
	
	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()

	HealthCheck(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	assert.Contains(t, w.Body.String(), "ok")
}

func TestCreateBook(t *testing.T) {
	mockStore := setupTest()

	bookReq := map[string]interface{}{
		"title":  "Test Book",
		"author": "Test Author",
		"year":   2024,
		"isbn":   "1234567890",
	}
	body, _ := json.Marshal(bookReq)

	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	CreateBook(w, req)

	assert.Equal(t, http.StatusCreated, w.Code)

	var response map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &response)
	assert.Equal(t, "Test Book", response["title"])
	assert.Equal(t, "Test Author", response["author"])
	
	// Verify book was added to mock store
	assert.Len(t, mockStore.books, 1)
}

func TestCreateBookMissingFields(t *testing.T) {
	setupTest()

	// Missing author
	bookReq := map[string]interface{}{
		"title": "Test Book",
		"year":  2024,
	}
	body, _ := json.Marshal(bookReq)

	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	CreateBook(w, req)

	assert.Equal(t, http.StatusBadRequest, w.Code)
	assert.Contains(t, w.Body.String(), "Validation failed")
}

func TestListBooks(t *testing.T) {
	mockStore := setupTest()

	// Add a test book
	mockStore.Create(&models.BookRequest{
		Title:  "List Test Book",
		Author: "List Author",
		Year:   2024,
		ISBN:   "123",
	})

	req := httptest.NewRequest("GET", "/books", nil)
	w := httptest.NewRecorder()

	ListBooks(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var books []map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &books)
	assert.Equal(t, 1, len(books))
}

func TestListBooksEmpty(t *testing.T) {
	setupTest()

	req := httptest.NewRequest("GET", "/books", nil)
	w := httptest.NewRecorder()

	ListBooks(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var books []map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &books)
	assert.Equal(t, 0, len(books))
}

func TestGetBookNotFound(t *testing.T) {
	setupTest()

	req := newRequestWithChiContext("GET", "/books/nonexistent", "nonexistent", nil)
	w := httptest.NewRecorder()

	GetBook(w, req)

	assert.Equal(t, http.StatusNotFound, w.Code)
	assert.Contains(t, w.Body.String(), "Book not found")
}

func TestUpdateBook(t *testing.T) {
	mockStore := setupTest()

	// Add a test book
	mockStore.Create(&models.BookRequest{
		Title:  "Original Title",
		Author: "Original Author",
		Year:   2024,
	})

	// Update it
	updateReq := map[string]interface{}{
		"title":  "Updated Title",
		"author": "Updated Author",
		"year":   2025,
		"isbn":   "updated-isbn",
	}
	body, _ := json.Marshal(updateReq)

	req := newRequestWithChiContext("PUT", "/books/test-id-123", "test-id-123", body)
	w := httptest.NewRecorder()

	UpdateBook(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var response map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &response)
	assert.Equal(t, "Updated Title", response["title"])
	assert.Equal(t, "Updated Author", response["author"])
}

func TestUpdateBookNotFound(t *testing.T) {
	setupTest()

	updateReq := map[string]interface{}{
		"title":  "Updated Title",
		"author": "Updated Author",
		"year":   2025,
	}
	body, _ := json.Marshal(updateReq)

	req := newRequestWithChiContext("PUT", "/books/nonexistent", "nonexistent", body)
	w := httptest.NewRecorder()

	UpdateBook(w, req)

	assert.Equal(t, http.StatusNotFound, w.Code)
	assert.Contains(t, w.Body.String(), "Book not found")
}

func TestDeleteBook(t *testing.T) {
	mockStore := setupTest()

	// Add a test book
	mockStore.Create(&models.BookRequest{
		Title:  "Delete Test Book",
		Author: "Delete Author",
		Year:   2024,
	})

	req := newRequestWithChiContext("DELETE", "/books/test-id-123", "test-id-123", nil)
	w := httptest.NewRecorder()

	DeleteBook(w, req)

	assert.Equal(t, http.StatusNoContent, w.Code)
	
	// Verify book was removed
	assert.Len(t, mockStore.books, 0)
}

func TestDeleteBookNotFound(t *testing.T) {
	setupTest()

	req := newRequestWithChiContext("DELETE", "/books/nonexistent", "nonexistent", nil)
	w := httptest.NewRecorder()

	DeleteBook(w, req)

	assert.Equal(t, http.StatusNotFound, w.Code)
	assert.Contains(t, w.Body.String(), "Book not found")
}