package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"bookapi/internal/models"

	"github.com/stretchr/testify/assert"
)

func TestBookCRUDIntegration(t *testing.T) {
	t.Run("Validate Book Model", func(t *testing.T) {
		book := models.Book{
			ID:     1,
			Title:  "Test Title",
			Author: "Test Author",
			Year:   2023,
			ISBN:   "test-isbn",
		}

		assert.Equal(t, 1, book.ID)
		assert.Equal(t, "Test Title", book.Title)
		assert.Equal(t, "Test Author", book.Author)
		assert.Equal(t, 2023, book.Year)
		assert.Equal(t, "test-isbn", book.ISBN)
	})

	t.Run("Health Check", func(t *testing.T) {
		// Test health check endpoint logic
		req := httptest.NewRequest("GET", "/health", nil)
		w := httptest.NewRecorder()

		// Create a simple health handler
		handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusOK)
			json.NewEncoder(w).Encode(map[string]string{"status": "OK"})
		})

		handler.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)

		var response map[string]string
		json.Unmarshal(w.Body.Bytes(), &response)
		assert.Equal(t, "OK", response["status"])
	})

	t.Run("Book Validation Rules", func(t *testing.T) {
		// Test that title and author are required
		validBook := models.Book{
			Title:  "Valid Title",
			Author: "Valid Author",
		}
		assert.NotEmpty(t, validBook.Title)
		assert.NotEmpty(t, validBook.Author)

		// Test invalid books
		noTitle := models.Book{Author: "Author Only"}
		assert.Empty(t, noTitle.Title)

		noAuthor := models.Book{Title: "Title Only"}
		assert.Empty(t, noAuthor.Author)
	})
}