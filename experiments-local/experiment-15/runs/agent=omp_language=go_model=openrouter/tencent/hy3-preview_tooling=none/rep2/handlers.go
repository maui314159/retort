package main

import (
	"encoding/json"
	"log"
	"net/http"
	"strconv"
	"strings"
)

type Handler struct {
	storage *Storage
}

func NewHandler(storage *Storage) *Handler {
	return &Handler{storage: storage}
}

func (h *Handler) CreateBook(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req CreateBookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		h.respondWithError(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	if req.Title == "" || req.Author == "" {
		h.respondWithError(w, "Title and author are required", http.StatusBadRequest)
		return
	}

	book := &Book{
		Title:  req.Title,
		Author: req.Author,
		Year:   req.Year,
		ISBN:   req.ISBN,
	}

	if err := h.storage.CreateBook(book); err != nil {
		log.Printf("Failed to create book: %v", err)
		h.respondWithError(w, "Failed to create book", http.StatusInternalServerError)
		return
	}

	h.respondWithJSON(w, book, http.StatusCreated)
}

func (h *Handler) GetBooks(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	authorFilter := r.URL.Query().Get("author")
	books, err := h.storage.GetAllBooks(authorFilter)
	if err != nil {
		log.Printf("Failed to get books: %v", err)
		h.respondWithError(w, "Failed to get books", http.StatusInternalServerError)
		return
	}

	h.respondWithJSON(w, books, http.StatusOK)
}

func (h *Handler) GetBook(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	id, err := h.extractIDFromPath(r.URL.Path)
	if err != nil {
		h.respondWithError(w, "Invalid book ID", http.StatusBadRequest)
		return
	}

	book, err := h.storage.GetBookByID(id)
	if err != nil {
		if strings.Contains(err.Error(), "not found") {
			h.respondWithError(w, "Book not found", http.StatusNotFound)
			return
		}
		log.Printf("Failed to get book: %v", err)
		h.respondWithError(w, "Failed to get book", http.StatusInternalServerError)
		return
	}

	h.respondWithJSON(w, book, http.StatusOK)
}

func (h *Handler) UpdateBook(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPut {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	id, err := h.extractIDFromPath(r.URL.Path)
	if err != nil {
		h.respondWithError(w, "Invalid book ID", http.StatusBadRequest)
		return
	}

	var req UpdateBookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		h.respondWithError(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	if err := h.storage.UpdateBook(id, &req); err != nil {
		if strings.Contains(err.Error(), "not found") {
			h.respondWithError(w, "Book not found", http.StatusNotFound)
			return
		}
		log.Printf("Failed to update book: %v", err)
		h.respondWithError(w, "Failed to update book", http.StatusInternalServerError)
		return
	}

	book, _ := h.storage.GetBookByID(id)
	h.respondWithJSON(w, book, http.StatusOK)
}

func (h *Handler) DeleteBook(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodDelete {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	id, err := h.extractIDFromPath(r.URL.Path)
	if err != nil {
		h.respondWithError(w, "Invalid book ID", http.StatusBadRequest)
		return
	}

	if err := h.storage.DeleteBook(id); err != nil {
		if strings.Contains(err.Error(), "not found") {
			h.respondWithError(w, "Book not found", http.StatusNotFound)
			return
		}
		log.Printf("Failed to delete book: %v", err)
		h.respondWithError(w, "Failed to delete book", http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

func (h *Handler) HealthCheck(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	response := HealthResponse{Status: "healthy"}
	h.respondWithJSON(w, response, http.StatusOK)
}

func (h *Handler) extractIDFromPath(path string) (int64, error) {
	parts := strings.Split(path, "/")
	if len(parts) < 3 {
		return 0, strconv.ErrSyntax
	}

	id, err := strconv.ParseInt(parts[2], 10, 64)
	if err != nil {
		return 0, err
	}
	return id, nil
}

func (h *Handler) respondWithJSON(w http.ResponseWriter, data interface{}, statusCode int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	json.NewEncoder(w).Encode(data)
}

func (h *Handler) respondWithError(w http.ResponseWriter, message string, statusCode int) {
	response := ErrorResponse{Error: message}
	h.respondWithJSON(w, response, statusCode)
}
