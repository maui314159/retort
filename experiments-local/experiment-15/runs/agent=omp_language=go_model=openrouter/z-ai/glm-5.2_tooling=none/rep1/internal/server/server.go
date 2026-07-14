// Package server wires the book store to HTTP handlers using the
// standard-library ServeMux (Go 1.22+ method routing).
package server

import (
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"strconv"

	"bookapi/internal/book"
)

type Server struct {
	Store *book.Store
	// Now is injectable so tests can fix the clock for year validation.
}

// New returns an http.Handler with all routes registered.
func New(s *book.Store) http.Handler {
	srv := &Server{Store: s}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", srv.health)
	mux.HandleFunc("POST /books", srv.createBook)
	mux.HandleFunc("GET /books", srv.listBooks)
	mux.HandleFunc("GET /books/{id}", srv.getBook)
	mux.HandleFunc("PUT /books/{id}", srv.updateBook)
	mux.HandleFunc("DELETE /books/{id}", srv.deleteBook)
	return logging(mux)
}

// --- handlers ---

func (s *Server) health(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) createBook(w http.ResponseWriter, r *http.Request) {
	var b book.Book
	if err := decodeJSON(r, &b); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body")
		return
	}
	created, err := s.Store.Create(r.Context(), b)
	if err != nil {
		if errors.Is(err, book.ErrValidation) {
			writeError(w, http.StatusBadRequest, "title and author are required; isbn must be 10 or 13 digits; year must be valid")
			return
		}
		writeError(w, http.StatusInternalServerError, "could not create book")
		return
	}
	writeJSON(w, http.StatusCreated, created)
}

func (s *Server) listBooks(w http.ResponseWriter, r *http.Request) {
	author := r.URL.Query().Get("author")
	books, err := s.Store.List(r.Context(), author)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not list books")
		return
	}
	if books == nil {
		books = []book.Book{}
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *Server) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	b, err := s.Store.Get(r.Context(), id)
	if err != nil {
		if errors.Is(err, book.ErrNotFound) {
			writeError(w, http.StatusNotFound, "book not found")
			return
		}
		writeError(w, http.StatusInternalServerError, "could not get book")
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (s *Server) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	var b book.Book
	if err := decodeJSON(r, &b); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body")
		return
	}
	updated, err := s.Store.Update(r.Context(), id, b)
	if err != nil {
		if errors.Is(err, book.ErrValidation) {
			writeError(w, http.StatusBadRequest, "title and author are required; isbn must be 10 or 13 digits; year must be valid")
			return
		}
		if errors.Is(err, book.ErrNotFound) {
			writeError(w, http.StatusNotFound, "book not found")
			return
		}
		writeError(w, http.StatusInternalServerError, "could not update book")
		return
	}
	writeJSON(w, http.StatusOK, updated)
}

func (s *Server) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	if err := s.Store.Delete(r.Context(), id); err != nil {
		if errors.Is(err, book.ErrNotFound) {
			writeError(w, http.StatusNotFound, "book not found")
			return
		}
		writeError(w, http.StatusInternalServerError, "could not delete book")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// --- helpers ---

func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	idStr := r.PathValue("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return 0, false
	}
	return id, true
}

func decodeJSON(r *http.Request, dst any) error {
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	defer r.Body.Close()
	return dec.Decode(dst)
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

type errBody struct {
	Error string `json:"error"`
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, errBody{Error: msg})
}

// logging is a minimal request logger middleware.
func logging(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Strip the JSON-RPC-ish verbosity; keep one line per request.
		log.Printf("%s %s", r.Method, r.URL.Path)
		next.ServeHTTP(w, r)
	})
}
