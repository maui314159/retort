package main

import (
	"encoding/json"
	"errors"
	"net/http"
	"strconv"
	"strings"
)

// handlers holds shared dependencies for the HTTP handlers.
type handlers struct {
	store *Store
}

func (h *handlers) routes() *http.ServeMux {
	mux := http.NewServeMux()
	mux.HandleFunc("/health", h.health)
	mux.HandleFunc("/books", h.booksRoot)
	// The trailing-slash-less pattern "/books/" matches paths like
	// "/books/{id}". We dispatch within the handler.
	mux.HandleFunc("/books/", h.bookByID)
	return mux
}

// health responds 200 OK for liveness/readiness probes.
func (h *handlers) health(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (h *handlers) booksRoot(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodPost:
		h.createBook(w, r)
	case http.MethodGet:
		h.listBooks(w, r)
	default:
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
	}
}

func (h *handlers) bookByID(w http.ResponseWriter, r *http.Request) {
	// r.URL.Path looks like "/books/{id}"
	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	if idStr == "" {
		http.NotFound(w, r)
		return
	}
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil || id < 1 {
		writeJSON(w, http.StatusBadRequest, errResp("invalid book id"))
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
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
	}
}

func (h *handlers) createBook(w http.ResponseWriter, r *http.Request) {
	inp, ok := decodeBook(w, r)
	if !ok {
		return
	}
	if errs := validateCreate(inp); len(errs) > 0 {
		writeJSON(w, http.StatusBadRequest, errResp(strings.Join(errs, "; ")))
		return
	}
	b, err := h.store.Create(*inp.Title, *inp.Author, inp.Year, deref(inp.ISBN))
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, errResp("could not create book"))
		return
	}
	writeJSON(w, http.StatusCreated, b)
}

func (h *handlers) listBooks(w http.ResponseWriter, r *http.Request) {
	author := r.URL.Query().Get("author")
	books, err := h.store.List(author)
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, errResp("could not list books"))
		return
	}
	if books == nil {
		books = []Book{}
	}
	writeJSON(w, http.StatusOK, books)
}

func (h *handlers) getBook(w http.ResponseWriter, r *http.Request, id int64) {
	b, err := h.store.Get(id)
	if err != nil {
		if errors.Is(err, ErrNotFound) {
			writeJSON(w, http.StatusNotFound, errResp("book not found"))
			return
		}
		writeJSON(w, http.StatusInternalServerError, errResp("could not get book"))
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (h *handlers) updateBook(w http.ResponseWriter, r *http.Request, id int64) {
	inp, ok := decodeBook(w, r)
	if !ok {
		return
	}
	if errs := validateUpdate(inp); len(errs) > 0 {
		writeJSON(w, http.StatusBadRequest, errResp(strings.Join(errs, "; ")))
		return
	}
	b, err := h.store.Update(id, *inp)
	if err != nil {
		if errors.Is(err, ErrNotFound) {
			writeJSON(w, http.StatusNotFound, errResp("book not found"))
			return
		}
		writeJSON(w, http.StatusInternalServerError, errResp("could not update book"))
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (h *handlers) deleteBook(w http.ResponseWriter, r *http.Request, id int64) {
	if err := h.store.Delete(id); err != nil {
		writeJSON(w, http.StatusInternalServerError, errResp("could not delete book"))
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// decodeBook reads and unmarshals the JSON body into a bookInput.
func decodeBook(w http.ResponseWriter, r *http.Request) (*bookInput, bool) {
	var inp bookInput
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(&inp); err != nil {
		writeJSON(w, http.StatusBadRequest, errResp("invalid JSON body"))
		return nil, false
	}
	return &inp, true
}

// validateCreate enforces that title and author are required and non-empty.
func validateCreate(inp *bookInput) []string {
	var errs []string
	if inp.Title == nil || strings.TrimSpace(*inp.Title) == "" {
		errs = append(errs, "title is required")
	}
	if inp.Author == nil || strings.TrimSpace(*inp.Author) == "" {
		errs = append(errs, "author is required")
	}
	return errs
}

// validateUpdate enforces requiredness only for fields that are present.
func validateUpdate(inp *bookInput) []string {
	var errs []string
	if inp.Title != nil && strings.TrimSpace(*inp.Title) == "" {
		errs = append(errs, "title must not be empty")
	}
	if inp.Author != nil && strings.TrimSpace(*inp.Author) == "" {
		errs = append(errs, "author must not be empty")
	}
	return errs
}

// errResp builds a small JSON error envelope.
type errResp string

func (e errResp) MarshalJSON() ([]byte, error) {
	return json.Marshal(map[string]string{"error": string(e)})
}

// deref safely dereferences a *string, returning "" for nil.
func deref(s *string) string {
	if s == nil {
		return ""
	}
	return *s
}

// writeJSON serializes v as JSON with the given status code.
func writeJSON(w http.ResponseWriter, status int, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	enc := json.NewEncoder(w)
	_ = enc.Encode(v)
}
