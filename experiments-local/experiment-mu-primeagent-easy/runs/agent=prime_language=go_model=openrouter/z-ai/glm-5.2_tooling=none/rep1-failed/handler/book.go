package handler

import (
	"encoding/json"
	"log"
	"net/http"
	"strconv"
	"strings"

	"github.com/example/bookapi/model"
)

// Handler exposes the book API as HTTP endpoints.
type Handler struct {
	store BookStore
}

// BookStore is the subset of the storage layer used by the handler. It is
// defined as an interface so the handler can be tested with a fake store.
type BookStore interface {
	Create(b model.BookInput) (model.Book, error)
	List(author string) ([]model.Book, error)
	Get(id int) (model.Book, bool, error)
	Update(id int, b model.BookInput) (model.Book, bool, error)
	Delete(id int) (bool, error)
}

// NewHandler returns a Handler backed by the given store.
func NewHandler(s BookStore) *Handler {
	return &Handler{store: s}
}

// CreateBook handles POST /books.
func (h *Handler) CreateBook(w http.ResponseWriter, r *http.Request) {
	in, ok := decodeBookInput(w, r)
	if !ok {
		return
	}
	book, err := h.store.Create(in)
	if err != nil {
		log.Printf("create book: %v", err)
		writeError(w, http.StatusInternalServerError, "failed to create book")
		return
	}
	writeJSON(w, http.StatusCreated, book)
}

// ListBooks handles GET /books and supports an optional ?author= filter.
func (h *Handler) ListBooks(w http.ResponseWriter, r *http.Request) {
	author := r.URL.Query().Get("author")
	books, err := h.store.List(author)
	if err != nil {
		log.Printf("list books: %v", err)
		writeError(w, http.StatusInternalServerError, "failed to list books")
		return
	}
	if books == nil {
		books = []model.Book{}
	}
	writeJSON(w, http.StatusOK, books)
}

// GetBook handles GET /books/{id}.
func (h *Handler) GetBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	book, found, err := h.store.Get(id)
	if err != nil {
		log.Printf("get book: %v", err)
		writeError(w, http.StatusInternalServerError, "failed to get book")
		return
	}
	if !found {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	writeJSON(w, http.StatusOK, book)
}

// UpdateBook handles PUT /books/{id}.
func (h *Handler) UpdateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	in, ok := decodeBookInput(w, r)
	if !ok {
		return
	}
	book, updated, err := h.store.Update(id, in)
	if err != nil {
		log.Printf("update book: %v", err)
		writeError(w, http.StatusInternalServerError, "failed to update book")
		return
	}
	if !updated {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	writeJSON(w, http.StatusOK, book)
}

// DeleteBook handles DELETE /books/{id}.
func (h *Handler) DeleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	deleted, err := h.store.Delete(id)
	if err != nil {
		log.Printf("delete book: %v", err)
		writeError(w, http.StatusInternalServerError, "failed to delete book")
		return
	}
	if !deleted {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// Health handles GET /health.
func (h *Handler) Health(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func decodeBookInput(w http.ResponseWriter, r *http.Request) (model.BookInput, bool) {
	var in model.BookInput
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(&in); err != nil {
		if strings.TrimSpace(err.Error()) == "EOF" || strings.Contains(err.Error(), "EOF") {
			writeError(w, http.StatusBadRequest, "request body is required")
			return in, false
		}
		writeError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return in, false
	}
	if errs := in.Validate(); len(errs) > 0 {
		writeError(w, http.StatusBadRequest, strings.Join(errs, "; "))
		return in, false
	}
	return in, true
}

func parseID(w http.ResponseWriter, r *http.Request) (int, bool) {
	idStr := r.PathValue("id")
	id, err := strconv.Atoi(idStr)
	if err != nil || id <= 0 {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return 0, false
	}
	return id, true
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(v); err != nil {
		log.Printf("write json: %v", err)
	}
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}
