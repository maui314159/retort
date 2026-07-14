package main

import (
	"encoding/json"
	"net/http"
	"strconv"
	"strings"
)

// apiError is a small helper producing {"error": "..."} JSON responses.
func writeError(w http.ResponseWriter, status int, msg string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(map[string]string{"error": msg})
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

// booksHandler dispatches by method for /books (no ID).
func (s *server) booksHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodPost:
		s.createBook(w, r)
	case http.MethodGet:
		s.listBooksHandler(w, r)
	default:
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

// bookHandler dispatches by method for /books/{id}.
func (s *server) bookHandler(w http.ResponseWriter, r *http.Request) {
	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	idStr = strings.Trim(idStr, "/")
	if idStr == "" {
		writeError(w, http.StatusBadRequest, "missing book id")
		return
	}
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return
	}

	switch r.Method {
	case http.MethodGet:
		s.getBookHandler(w, r, id)
	case http.MethodPut:
		s.updateBookHandler(w, r, id)
	case http.MethodDelete:
		s.deleteBookHandler(w, r, id)
	default:
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

func (s *server) createBook(w http.ResponseWriter, r *http.Request) {
	in, ok := decodeBookInput(w, r)
	if !ok {
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
	created, err := insertBook(s.db, b)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusCreated, created)
}

func (s *server) listBooksHandler(w http.ResponseWriter, r *http.Request) {
	author := r.URL.Query().Get("author")
	books, err := listBooks(s.db, author)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if books == nil {
		books = []Book{}
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *server) getBookHandler(w http.ResponseWriter, r *http.Request, id int64) {
	b, err := getBook(s.db, id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if b == nil {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (s *server) updateBookHandler(w http.ResponseWriter, r *http.Request, id int64) {
	in, ok := decodeBookInput(w, r)
	if !ok {
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
	found, err := updateBook(s.db, id, b)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if !found {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	b.ID = id
	writeJSON(w, http.StatusOK, b)
}

func (s *server) deleteBookHandler(w http.ResponseWriter, r *http.Request, id int64) {
	found, err := deleteBook(s.db, id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if !found {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// decodeBookInput parses & validates the JSON body. Returns false on error
// (the response has already been written).
func decodeBookInput(w http.ResponseWriter, r *http.Request) (bookInput, bool) {
	var in bookInput
	if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body: "+err.Error())
		return in, false
	}
	if missing := in.validate(); len(missing) > 0 {
		writeError(w, http.StatusBadRequest,
			"missing required field(s): "+strings.Join(missing, ", "))
		return in, false
	}
	return in, true
}
