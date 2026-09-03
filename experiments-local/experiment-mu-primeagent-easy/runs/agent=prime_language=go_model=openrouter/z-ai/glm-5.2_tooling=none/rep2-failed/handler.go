package main

import (
	"encoding/json"
	"log"
	"net/http"
	"strconv"
	"strings"
)

// Handler bundles the HTTP handlers for the book API around a Store.
type Handler struct {
	store *Store
}

// NewHandler creates a Handler backed by the given Store.
func NewHandler(store *Store) *Handler {
	return &Handler{store: store}
}

// Routes registers all API routes on the given mux. It uses Go 1.22+
// ServeMux pattern matching so that {id} is captured as a path
// parameter.
func (h *Handler) Routes(mux *http.ServeMux) {
	mux.HandleFunc("GET /health", h.Health)
	mux.HandleFunc("GET /books", h.ListBooks)
	mux.HandleFunc("POST /books", h.CreateBook)
	mux.HandleFunc("GET /books/{id}", h.GetBook)
	mux.HandleFunc("PUT /books/{id}", h.UpdateBook)
	mux.HandleFunc("DELETE /books/{id}", h.DeleteBook)
}

// --- error helper -----------------------------------------------------

// errorResponse is the JSON body returned for all non-2xx responses.
type errorResponse struct {
	Error string `json:"error"`
}

func writeError(w http.ResponseWriter, status int, msg string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(errorResponse{Error: msg})
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

// parseID extracts and validates the {id} path parameter. On failure
// it writes a 400 response and returns ok=false.
func parseID(w http.ResponseWriter, idStr string) (int64, bool) {
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return 0, false
	}
	return id, true
}

// decodeBookInput reads and decodes a JSON body into BookInput. On a
// decode error it writes a 400 response and returns ok=false. An empty
// body is treated as a zero-value input (validation will then catch
// missing required fields).
func decodeBookInput(w http.ResponseWriter, r *http.Request) (BookInput, bool) {
	var in BookInput
	if r.Body == nil {
		return in, true
	}
	dec := json.NewDecoder(r.Body)
	if err := dec.Decode(&in); err != nil {
		if err.Error() == "EOF" || strings.Contains(err.Error(), "EOF") {
			return in, true
		}
		writeError(w, http.StatusBadRequest, "invalid JSON body")
		return in, false
	}
	return in, true
}

// --- handlers ---------------------------------------------------------

func (h *Handler) Health(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (h *Handler) CreateBook(w http.ResponseWriter, r *http.Request) {
	in, ok := decodeBookInput(w, r)
	if !ok {
		return
	}
	if status, err := in.Validate(); err != nil {
		writeError(w, status, err.Error())
		return
	}
	book, err := h.store.CreateBook(in)
	if err != nil {
		log.Printf("create book: %v", err)
		writeError(w, http.StatusInternalServerError, "failed to create book")
		return
	}
	writeJSON(w, http.StatusCreated, book)
}

func (h *Handler) ListBooks(w http.ResponseWriter, r *http.Request) {
	author := r.URL.Query().Get("author")
	books, err := h.store.ListBooks(author)
	if err != nil {
		log.Printf("list books: %v", err)
		writeError(w, http.StatusInternalServerError, "failed to list books")
		return
	}
	if books == nil {
		books = []Book{}
	}
	writeJSON(w, http.StatusOK, books)
}

func (h *Handler) GetBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r.PathValue("id"))
	if !ok {
		return
	}
	book, err := h.store.GetBook(id)
	if err != nil {
		log.Printf("get book: %v", err)
		writeError(w, http.StatusInternalServerError, "failed to get book")
		return
	}
	if book == nil {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (h *Handler) UpdateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r.PathValue("id"))
	if !ok {
		return
	}
	in, ok := decodeBookInput(w, r)
	if !ok {
		return
	}
	if status, err := in.Validate(); err != nil {
		writeError(w, status, err.Error())
		return
	}
	book, err := h.store.UpdateBook(id, in)
	if err != nil {
		log.Printf("update book: %v", err)
		writeError(w, http.StatusInternalServerError, "failed to update book")
		return
	}
	if book == nil {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (h *Handler) DeleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r.PathValue("id"))
	if !ok {
		return
	}
	deleted, err := h.store.DeleteBook(id)
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
