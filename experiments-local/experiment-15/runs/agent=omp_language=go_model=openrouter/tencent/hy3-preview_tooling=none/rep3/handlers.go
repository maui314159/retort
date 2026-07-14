package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"strings"
	"time"
	"unicode/utf8"
)

// Handler holds the dependencies for HTTP handlers
type Handler struct {
	store *BookStore
}

// NewHandler creates a new Handler with the given BookStore
func NewHandler(store *BookStore) *Handler {
	return &Handler{store: store}
}

// RegisterRoutes registers all routes on the given ServeMux
func (h *Handler) RegisterRoutes(mux *http.ServeMux) {
	mux.HandleFunc("/health", h.handleHealth)
	mux.HandleFunc("/books", h.handleBooks)
	mux.HandleFunc("/books/", h.handleBookByID)
}

// handleHealth handles GET /health
func (h *Handler) handleHealth(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	resp := HealthResponse{
		Status: "healthy",
		Time:   time.Now().Format(time.RFC3339),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

// handleBooks handles GET /books and POST /books
func (h *Handler) handleBooks(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		h.listBooks(w, r)
	case http.MethodPost:
		h.createBook(w, r)
	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

// handleBookByID handles GET /books/{id}, PUT /books/{id}, DELETE /books/{id}
func (h *Handler) handleBookByID(w http.ResponseWriter, r *http.Request) {
	// Extract ID from path: /books/{id}
	path := strings.TrimPrefix(r.URL.Path, "/books/")
	if path == "" {
		http.Error(w, "Book ID required", http.StatusBadRequest)
		return
	}

	id, err := strconv.ParseInt(path, 10, 64)
	if err != nil {
		h.writeError(w, "Invalid book ID", http.StatusBadRequest)
		return
	}

	switch r.Method {
	case http.MethodGet:
		h.getBook(w, r, id)
	case http.MethodPut:
		h.updateBook(w, r, id)
	case http.MethodDelete:
		h.deleteBook(w, r, id)
	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

// listBooks handles GET /books
func (h *Handler) listBooks(w http.ResponseWriter, r *http.Request) {
	authorFilter := r.URL.Query().Get("author")

	books, err := h.store.ListBooks(authorFilter)
	if err != nil {
		log.Printf("Error listing books: %v", err)
		h.writeError(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(books)
}

// createBook handles POST /books
func (h *Handler) createBook(w http.ResponseWriter, r *http.Request) {
	var req CreateBookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		h.writeError(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	// Validate input
	if err := validateCreateBookRequest(req); err != nil {
		h.writeError(w, err.Error(), http.StatusBadRequest)
		return
	}

	book, err := h.store.CreateBook(req)
	if err != nil {
		log.Printf("Error creating book: %v", err)
		h.writeError(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(book)
}

// getBook handles GET /books/{id}
func (h *Handler) getBook(w http.ResponseWriter, r *http.Request, id int64) {
	book, err := h.store.GetBookByID(id)
	if err != nil {
		if strings.Contains(err.Error(), "not found") {
			h.writeError(w, err.Error(), http.StatusNotFound)
		} else {
			log.Printf("Error getting book: %v", err)
			h.writeError(w, "Internal server error", http.StatusInternalServerError)
		}
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(book)
}

// updateBook handles PUT /books/{id}
func (h *Handler) updateBook(w http.ResponseWriter, r *http.Request, id int64) {
	var req UpdateBookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		h.writeError(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	// Validate that at least one field is being updated
	if req.Title == nil && req.Author == nil && req.Year == nil && req.ISBN == nil {
		h.writeError(w, "At least one field must be provided for update", http.StatusBadRequest)
		return
	}

	// Validate title if provided
	if req.Title != nil {
		if *req.Title == "" {
			h.writeError(w, "Title cannot be empty", http.StatusBadRequest)
			return
		}
		if !isPrintableASCII(*req.Title) {
			h.writeError(w, "Title must contain only printable characters", http.StatusBadRequest)
			return
		}
		if utf8.RuneCountInString(*req.Title) > 500 {
			h.writeError(w, "Title must not exceed 500 characters", http.StatusBadRequest)
			return
		}
	}

	// Validate author if provided
	if req.Author != nil {
		if *req.Author == "" {
			h.writeError(w, "Author cannot be empty", http.StatusBadRequest)
			return
		}
		if !isPrintableASCII(*req.Author) {
			h.writeError(w, "Author must contain only printable characters", http.StatusBadRequest)
			return
		}
		if utf8.RuneCountInString(*req.Author) > 200 {
			h.writeError(w, "Author must not exceed 200 characters", http.StatusBadRequest)
			return
		}
	}

	book, err := h.store.UpdateBook(id, req)
	if err != nil {
		if strings.Contains(err.Error(), "not found") {
			h.writeError(w, err.Error(), http.StatusNotFound)
		} else {
			log.Printf("Error updating book: %v", err)
			h.writeError(w, "Internal server error", http.StatusInternalServerError)
		}
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(book)
}

// deleteBook handles DELETE /books/{id}
func (h *Handler) deleteBook(w http.ResponseWriter, r *http.Request, id int64) {
	err := h.store.DeleteBook(id)
	if err != nil {
		if strings.Contains(err.Error(), "not found") {
			h.writeError(w, err.Error(), http.StatusNotFound)
		} else {
			log.Printf("Error deleting book: %v", err)
			h.writeError(w, "Internal server error", http.StatusInternalServerError)
		}
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

// validateCreateBookRequest validates a create book request
func validateCreateBookRequest(req CreateBookRequest) error {
	if req.Title == "" {
		return fmt.Errorf("Title is required")
	}
	if req.Author == "" {
		return fmt.Errorf("Author is required")
	}
	if !isPrintableASCII(req.Title) {
		return fmt.Errorf("Title must contain only printable characters")
	}
	if !isPrintableASCII(req.Author) {
		return fmt.Errorf("Author must contain only printable characters")
	}
	if utf8.RuneCountInString(req.Title) > 500 {
		return fmt.Errorf("Title must not exceed 500 characters")
	}
	if utf8.RuneCountInString(req.Author) > 200 {
		return fmt.Errorf("Author must not exceed 200 characters")
	}
	return nil
}

// isPrintableASCII checks if a string contains only printable ASCII characters
func isPrintableASCII(s string) bool {
	for _, r := range s {
		if r < 32 || r > 126 {
			return false
		}
	}
	return true
}

// writeError writes a JSON error response
func (h *Handler) writeError(w http.ResponseWriter, message string, status int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(ErrorResponse{Error: message})
}
