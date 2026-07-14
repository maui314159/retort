package handlers

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	"bookapi/internal/database"
)

// Handlers holds the database connection
type Handlers struct {
	db *database.DB
}

func NewHandlers(db *database.DB) *Handlers {
	return &Handlers{db: db}
}

// HealthCheck handles GET /health
func (h *Handlers) HealthCheck(c *gin.Context) {
	if err := h.db.HealthCheck(); err != nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"status": "unhealthy", "error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": "healthy"})
}

// CreateBook handles POST /books
func (h *Handlers) CreateBook(c *gin.Context) {
	var book database.Book
	if err := c.ShouldBindJSON(&book); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid request body: " + err.Error()})
		return
	}

	// Validation: title and author are required
	if book.Title == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "title is required"})
		return
	}
	if book.Author == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "author is required"})
		return
	}

	if err := h.db.CreateBook(&book); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to create book: " + err.Error()})
		return
	}

	c.JSON(http.StatusCreated, book)
}

// GetBook handles GET /books/:id
func (h *Handlers) GetBook(c *gin.Context) {
	idStr := c.Param("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid book ID"})
		return
	}

	book, err := h.db.GetBookByID(id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to get book: " + err.Error()})
		return
	}

	if book == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "book not found"})
		return
	}

	c.JSON(http.StatusOK, book)
}

// ListBooks handles GET /books
func (h *Handlers) ListBooks(c *gin.Context) {
	// Parse optional query parameters for pagination
	limitStr := c.DefaultQuery("limit", "100")
	offsetStr := c.DefaultQuery("offset", "0")

	limit, err := strconv.Atoi(limitStr)
	if err != nil || limit <= 0 {
		limit = 100
	}
	if limit > 1000 {
		limit = 1000
	}

	offset, err := strconv.Atoi(offsetStr)
	if err != nil || offset < 0 {
		offset = 0
	}

	// Optional author filter
	author := c.Query("author")

	var books []*database.Book
	if author != "" {
		// For simplicity, we'll filter in memory since SQLite doesn't have a simple way
		// to do parameterized LIKE without changing the query structure
		allBooks, err := h.db.GetBooks(10000, 0) // Get all for filtering
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to list books: " + err.Error()})
			return
		}
		for _, b := range allBooks {
			if b.Author == author {
				books = append(books, b)
			}
		}
		// Apply pagination manually
		start := offset
		end := offset + limit
		if start >= len(books) {
			books = []*database.Book{}
		} else if end > len(books) {
			books = books[start:]
		} else {
			books = books[start:end]
		}
	} else {
		books, err = h.db.GetBooks(limit, offset)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to list books: " + err.Error()})
			return
		}
	}

	c.JSON(http.StatusOK, gin.H{
		"books": books,
		"count": len(books),
	})
}

// UpdateBook handles PUT /books/:id
func (h *Handlers) UpdateBook(c *gin.Context) {
	idStr := c.Param("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid book ID"})
		return
	}

	// Get existing book
	existingBook, err := h.db.GetBookByID(id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to get book: " + err.Error()})
		return
	}
	if existingBook == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "book not found"})
		return
	}

	// Parse request body
	var updateData database.Book
	if err := c.ShouldBindJSON(&updateData); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid request body: " + err.Error()})
		return
	}

	// Validation: title and author are required if provided
	if updateData.Title == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "title is required"})
		return
	}
	if updateData.Author == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "author is required"})
		return
	}

	// Update fields
	existingBook.Title = updateData.Title
	existingBook.Author = updateData.Author
	existingBook.Published = updateData.Published

	if err := h.db.UpdateBook(existingBook); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to update book: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, existingBook)
}

// DeleteBook handles DELETE /books/:id
func (h *Handlers) DeleteBook(c *gin.Context) {
	idStr := c.Param("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid book ID"})
		return
	}

	if err := h.db.DeleteBook(id); err != nil {
		if err.Error() == "sql: no rows in result set" {
			c.JSON(http.StatusNotFound, gin.H{"error": "book not found"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to delete book: " + err.Error()})
		return
	}

	c.Status(http.StatusNoContent)
}
