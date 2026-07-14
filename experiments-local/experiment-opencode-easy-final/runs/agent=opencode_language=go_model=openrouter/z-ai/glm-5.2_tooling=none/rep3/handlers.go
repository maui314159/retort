package main

import (
	"encoding/json"
	"net/http"
	"strconv"
	"strings"

	"github.com/gorilla/mux"
)

// Router builds the HTTP router for the book API.
func Router(s *Store) *mux.Router {
	r := mux.NewRouter()
	r.HandleFunc("/health", health).Methods(http.MethodGet)
	r.HandleFunc("/books", listBooks(s)).Methods(http.MethodGet).Queries("author", "{author}")
	r.HandleFunc("/books", listBooks(s)).Methods(http.MethodGet)
	r.HandleFunc("/books", createBook(s)).Methods(http.MethodPost)
	r.HandleFunc("/books/{id}", getBook(s)).Methods(http.MethodGet)
	r.HandleFunc("/books/{id}", updateBook(s)).Methods(http.MethodPut)
	r.HandleFunc("/books/{id}", deleteBook(s)).Methods(http.MethodDelete)
	r.Use(mux.CORSMethodMiddleware(r))
	return r
}

func health(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func listBooks(s *Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		author := strings.TrimSpace(r.URL.Query().Get("author"))
		books, err := s.List(author)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "failed to list books")
			return
		}
		if books == nil {
			books = []Book{}
		}
		writeJSON(w, http.StatusOK, books)
	}
}

func createBook(s *Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var in bookInput
		if err := decodeJSON(r, &in); err != nil {
			writeError(w, http.StatusBadRequest, "invalid JSON body")
			return
		}
		if errs := in.validate(); len(errs) > 0 {
			writeJSON(w, http.StatusUnprocessableEntity, map[string]any{
				"error":  "validation failed",
				"fields": errs,
			})
			return
		}
		b := Book{Title: *in.Title, Author: *in.Author, Year: in.Year}
		if in.ISBN != nil {
			b.ISBN = *in.ISBN
		}
		created, err := s.Create(b)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "failed to create book")
			return
		}
		writeJSON(w, http.StatusCreated, created)
	}
}

func getBook(s *Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		id, ok := idFromRequest(w, r)
		if !ok {
			return
		}
		b, err := s.Get(id)
		if err != nil {
			writeError(w, http.StatusNotFound, "book not found")
			return
		}
		writeJSON(w, http.StatusOK, b)
	}
}

func updateBook(s *Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		id, ok := idFromRequest(w, r)
		if !ok {
			return
		}
		var in bookInput
		if err := decodeJSON(r, &in); err != nil {
			writeError(w, http.StatusBadRequest, "invalid JSON body")
			return
		}
		if errs := in.validatePartial(); len(errs) > 0 {
			writeJSON(w, http.StatusUnprocessableEntity, map[string]any{
				"error":  "validation failed",
				"fields": errs,
			})
			return
		}
		updated, err := s.Update(id, in)
		if err != nil {
			writeError(w, http.StatusNotFound, "book not found")
			return
		}
		writeJSON(w, http.StatusOK, updated)
	}
}

func deleteBook(s *Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		id, ok := idFromRequest(w, r)
		if !ok {
			return
		}
		if _, err := s.Get(id); err != nil {
			writeError(w, http.StatusNotFound, "book not found")
			return
		}
		if err := s.Delete(id); err != nil {
			writeError(w, http.StatusInternalServerError, "failed to delete book")
			return
		}
		w.WriteHeader(http.StatusNoContent)
	}
}

func idFromRequest(w http.ResponseWriter, r *http.Request) (int64, bool) {
	v := mux.Vars(r)["id"]
	n, err := strconv.ParseInt(v, 10, 64)
	if err != nil || n < 1 {
		writeError(w, http.StatusBadRequest, "invalid id")
		return 0, false
	}
	return n, true
}

func decodeJSON(r *http.Request, dst any) error {
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	return dec.Decode(dst)
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}
