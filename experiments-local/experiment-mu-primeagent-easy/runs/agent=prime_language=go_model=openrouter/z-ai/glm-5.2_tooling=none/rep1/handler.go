package main

import (
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"strconv"
	"strings"
)

// Handler wires HTTP routes to the Store.
type Handler struct {
	store *Store
}

// NewHandler returns a Handler backed by the given Store.
func NewHandler(store *Store) *Handler {
	return &Handler{store: store}
}

// Routes builds the http.ServeMux with all application routes.
func (h *Handler) Routes() http.Handler {
	mux := http.NewServeMux()

	mux.HandleFunc("GET /health", h.health)
	mux.HandleFunc("GET /books", h.listBooks)
	mux.HandleFunc("POST /books", h.createBook)
	mux.HandleFunc("GET /books/{id}", h.getBook)
	mux.HandleFunc("PUT /books/{id}", h.updateBook)
	mux.HandleFunc("DELETE /books/{id}", h.deleteBook)

	return mux
}

// health responds with a simple ok status.
func (h *Handler) health(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

// listBooks handles GET /books with an optional ?author= filter.
func (h *Handler) listBooks(w http.ResponseWriter, r *http.Request) {
	author := strings.TrimSpace(r.URL.Query().Get("author"))
	books, err := h.store.ListBooks(author)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to list books")
		return
	}
	if books == nil {
		books = []Book{}
	}
	writeJSON(w, http.StatusOK, books)
}

// createBook handles POST /books.
func (h *Handler) createBook(w http.ResponseWriter, r *http.Request) {
	in, ok := decodeBookInput(w, r)
	if !ok {
		return
	}
	book, err := h.store.CreateBook(in)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to create book")
		return
	}
	writeJSON(w, http.StatusCreated, book)
}

// getBook handles GET /books/{id}.
func (h *Handler) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	book, found, err := h.store.GetBook(id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to get book")
		return
	}
	if !found {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	writeJSON(w, http.StatusOK, book)
}

// updateBook handles PUT /books/{id}.
func (h *Handler) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	in, ok := decodeBookInput(w, r)
	if !ok {
		return
	}
	book, found, err := h.store.UpdateBook(id, in)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to update book")
		return
	}
	if !found {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	writeJSON(w, http.StatusOK, book)
}

// deleteBook handles DELETE /books/{id}.
func (h *Handler) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	deleted, err := h.store.DeleteBook(id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to delete book")
		return
	}
	if !deleted {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// parseID extracts the {id} path variable and writes a 400 on failure.
func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	raw := r.PathValue("id")
	id, err := strconv.ParseInt(raw, 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return 0, false
	}
	return id, true
}

// decodeBookInput decodes the JSON body and validates it. It writes the
// appropriate error response and returns ok=false on failure.
func decodeBookInput(w http.ResponseWriter, r *http.Request) (BookInput, bool) {
	var in BookInput
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(&in); err != nil {
		if errors.Is(err, io.EOF) {
			writeError(w, http.StatusBadRequest, "request body is required")
			return BookInput{}, false
		}
		writeError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return BookInput{}, false
	}
	if err := in.Validate(); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return BookInput{}, false
	}
	return in, true
}

// writeJSON serializes v as JSON with the given status code.
func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

// writeError serializes a JSON error object.
func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}
