package main

import (
	"encoding/json"
	"io"
	"net/http"
	"strconv"
	"strings"
)

// errorResponse writes a JSON error with the given status code.
func errorResponse(w http.ResponseWriter, status int, msg string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(map[string]string{"error": msg})
}

// writeJSON serializes v as JSON with status code.
func writeJSON(w http.ResponseWriter, status int, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

// API holds dependencies for the HTTP handlers.
type API struct {
	Store *Store
}

// NewAPI constructs an API backed by the given Store.
func NewAPI(s *Store) *API { return &API{Store: s} }

// Handler returns the configured HTTP mux.
func (a *API) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/health", a.health)
	mux.HandleFunc("/books", a.booksRoot)
	mux.HandleFunc("/books/", a.booksByID)
	return mux
}

func (a *API) health(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		errorResponse(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (a *API) booksRoot(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodPost:
		a.createBook(w, r)
	case http.MethodGet:
		a.listBooks(w, r)
	default:
		errorResponse(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

func (a *API) booksByID(w http.ResponseWriter, r *http.Request) {
	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	if idStr == "" || strings.Contains(idStr, "/") {
		errorResponse(w, http.StatusNotFound, "not found")
		return
	}
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil || id < 1 {
		errorResponse(w, http.StatusBadRequest, "invalid book id")
		return
	}
	switch r.Method {
	case http.MethodGet:
		a.getBook(w, r, id)
	case http.MethodPut:
		a.updateBook(w, r, id)
	case http.MethodDelete:
		a.deleteBook(w, r, id)
	default:
		errorResponse(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

func (a *API) createBook(w http.ResponseWriter, r *http.Request) {
	body, err := io.ReadAll(r.Body)
	if err != nil {
		errorResponse(w, http.StatusBadRequest, "invalid request body")
		return
	}
	in, err := decodeBookInput(body)
	if err != nil {
		errorResponse(w, http.StatusBadRequest, "invalid JSON body")
		return
	}
	if errs := in.validate(false); len(errs) > 0 {
		writeJSON(w, http.StatusBadRequest, map[string][]string{"errors": errs})
		return
	}
	b := &Book{
		Title:  *in.Title,
		Author: *in.Author,
	}
	if in.Year != nil {
		b.Year = *in.Year
	}
	if in.ISBN != nil {
		b.ISBN = *in.ISBN
	}
	created, err := a.Store.Create(b)
	if err != nil {
		errorResponse(w, http.StatusInternalServerError, "failed to create book")
		return
	}
	writeJSON(w, http.StatusCreated, created)
}

func (a *API) listBooks(w http.ResponseWriter, r *http.Request) {
	author := r.URL.Query().Get("author")
	books, err := a.Store.List(author)
	if err != nil {
		errorResponse(w, http.StatusInternalServerError, "failed to list books")
		return
	}
	if books == nil {
		books = []Book{}
	}
	writeJSON(w, http.StatusOK, books)
}

func (a *API) getBook(w http.ResponseWriter, r *http.Request, id int64) {
	b, err := a.Store.Get(id)
	if err != nil {
		errorResponse(w, http.StatusInternalServerError, "failed to fetch book")
		return
	}
	if b == nil {
		errorResponse(w, http.StatusNotFound, "book not found")
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (a *API) updateBook(w http.ResponseWriter, r *http.Request, id int64) {
	body, err := io.ReadAll(r.Body)
	if err != nil {
		errorResponse(w, http.StatusBadRequest, "invalid request body")
		return
	}
	in, err := decodeBookInput(body)
	if err != nil {
		errorResponse(w, http.StatusBadRequest, "invalid JSON body")
		return
	}
	// PUT is a full replace: require title and author.
	if errs := in.validate(true); len(errs) > 0 {
		writeJSON(w, http.StatusBadRequest, map[string][]string{"errors": errs})
		return
	}
	b := &Book{
		ID:     id,
		Title:  *in.Title,
		Author: *in.Author,
	}
	if in.Year != nil {
		b.Year = *in.Year
	}
	if in.ISBN != nil {
		b.ISBN = *in.ISBN
	}
	ok, err := a.Store.Update(id, b)
	if err != nil {
		errorResponse(w, http.StatusInternalServerError, "failed to update book")
		return
	}
	if !ok {
		errorResponse(w, http.StatusNotFound, "book not found")
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (a *API) deleteBook(w http.ResponseWriter, r *http.Request, id int64) {
	ok, err := a.Store.Delete(id)
	if err != nil {
		errorResponse(w, http.StatusInternalServerError, "failed to delete book")
		return
	}
	if !ok {
		errorResponse(w, http.StatusNotFound, "book not found")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}
