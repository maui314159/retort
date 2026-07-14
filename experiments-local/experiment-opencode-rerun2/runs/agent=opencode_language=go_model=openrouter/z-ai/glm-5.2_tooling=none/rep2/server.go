package main

import (
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"strconv"
	"strings"
)

// Server wires the HTTP routes to the Store.
type Server struct {
	store *Store
	mux   *http.ServeMux
}

// NewServer builds a Server with the given store.
func NewServer(store *Store) *Server {
	s := &Server{store: store, mux: http.NewServeMux()}
	s.routes()
	return s
}

func (s *Server) routes() {
	s.mux.HandleFunc("/health", s.handleHealth)
	s.mux.HandleFunc("/books", s.handleBooks)
	s.mux.HandleFunc("/books/", s.handleBookByID)
}

// ServeHTTP implements http.Handler.
func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	s.mux.ServeHTTP(w, r)
}

// handlerFunc is a handler that returns an error for centralized handling.
type handlerFunc func(http.ResponseWriter, *http.Request) error

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) handleBooks(w http.ResponseWriter, r *http.Request) {
	var err error
	switch r.Method {
	case http.MethodPost:
		err = s.createBook(w, r)
	case http.MethodGet:
		err = s.listBooks(w, r)
	default:
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	if err != nil {
		writeErr(w, err)
	}
}

func (s *Server) handleBookByID(w http.ResponseWriter, r *http.Request) {
	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	if idStr == "" || strings.Contains(idStr, "/") {
		writeError(w, http.StatusNotFound, "not found")
		return
	}
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid id")
		return
	}

	switch r.Method {
	case http.MethodGet:
		err = s.getBook(w, r, id)
	case http.MethodPut:
		err = s.updateBook(w, r, id)
	case http.MethodDelete:
		err = s.deleteBook(w, r, id)
	default:
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	if err != nil {
		writeErr(w, err)
	}
}

func (s *Server) createBook(w http.ResponseWriter, r *http.Request) error {
	in, err := decodeBookInput(r)
	if err != nil {
		return err
	}
	if verr := validateInput(in, true); verr != nil {
		return verr
	}
	book := Book{
		Title:  *in.Title,
		Author: *in.Author,
		Year:   derefInt(in.Year),
		ISBN:   derefStr(in.ISBN),
	}
	created, err := s.store.Create(book)
	if err != nil {
		return err
	}
	writeJSON(w, http.StatusCreated, created)
	return nil
}

func (s *Server) listBooks(w http.ResponseWriter, r *http.Request) error {
	author := r.URL.Query().Get("author")
	books, err := s.store.List(author)
	if err != nil {
		return err
	}
	if books == nil {
		books = []Book{}
	}
	writeJSON(w, http.StatusOK, books)
	return nil
}

func (s *Server) getBook(w http.ResponseWriter, r *http.Request, id int64) error {
	b, err := s.store.Get(id)
	if err != nil {
		return err
	}
	writeJSON(w, http.StatusOK, b)
	return nil
}

func (s *Server) updateBook(w http.ResponseWriter, r *http.Request, id int64) error {
	in, err := decodeBookInput(r)
	if err != nil {
		return err
	}
	if verr := validateInput(in, false); verr != nil {
		return verr
	}
	existing, err := s.store.Get(id)
	if err != nil {
		return err
	}
	if in.Title != nil {
		existing.Title = *in.Title
	}
	if in.Author != nil {
		existing.Author = *in.Author
	}
	if in.Year != nil {
		existing.Year = *in.Year
	}
	if in.ISBN != nil {
		existing.ISBN = *in.ISBN
	}
	updated, err := s.store.Update(id, existing)
	if err != nil {
		return err
	}
	writeJSON(w, http.StatusOK, updated)
	return nil
}

func (s *Server) deleteBook(w http.ResponseWriter, r *http.Request, id int64) error {
	if err := s.store.Delete(id); err != nil {
		return err
	}
	w.WriteHeader(http.StatusNoContent)
	return nil
}

// --- helpers ---

// ValidationError describes invalid input.
type ValidationError struct {
	Status int
	Msg    string
}

func (e *ValidationError) Error() string { return e.Msg }

func decodeBookInput(r *http.Request) (BookInput, error) {
	var in BookInput
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(&in); err != nil {
		return in, &ValidationError{Status: http.StatusBadRequest, Msg: "invalid JSON body: " + err.Error()}
	}
	return in, nil
}

func validateInput(in BookInput, requireAll bool) error {
	if requireAll {
		if in.Title == nil || strings.TrimSpace(*in.Title) == "" {
			return &ValidationError{Status: http.StatusBadRequest, Msg: "title is required"}
		}
		if in.Author == nil || strings.TrimSpace(*in.Author) == "" {
			return &ValidationError{Status: http.StatusBadRequest, Msg: "author is required"}
		}
		return nil
	}
	// Partial update: validate any provided fields.
	if in.Title != nil && strings.TrimSpace(*in.Title) == "" {
		return &ValidationError{Status: http.StatusBadRequest, Msg: "title must not be empty"}
	}
	if in.Author != nil && strings.TrimSpace(*in.Author) == "" {
		return &ValidationError{Status: http.StatusBadRequest, Msg: "author must not be empty"}
	}
	return nil
}

func derefStr(s *string) string {
	if s == nil {
		return ""
	}
	return *s
}

func derefInt(i *int) int {
	if i == nil {
		return 0
	}
	return *i
}

func writeJSON(w http.ResponseWriter, status int, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

func writeErr(w http.ResponseWriter, err error) {
	var ve *ValidationError
	if errors.As(err, &ve) {
		writeError(w, ve.Status, ve.Msg)
		return
	}
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	log.Printf("internal error: %v", err)
	writeError(w, http.StatusInternalServerError, "internal server error")
}
