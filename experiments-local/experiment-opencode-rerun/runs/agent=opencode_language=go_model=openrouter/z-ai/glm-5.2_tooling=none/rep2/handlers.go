package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"strconv"
	"strings"
)

type apiServer struct {
	db *sql.DB
}

func newAPIServer(db *sql.DB) *apiServer { return &apiServer{db: db} }

// registerRoutes wires up handlers using Go 1.22+ ServeMux patterns.
func (s *apiServer) registerRoutes(mux *http.ServeMux) {
	mux.HandleFunc("GET /health", s.health)
	mux.HandleFunc("POST /books", s.createBook)
	mux.HandleFunc("GET /books", s.listBooks)
	mux.HandleFunc("GET /books/{id}", s.getBook)
	mux.HandleFunc("PUT /books/{id}", s.updateBook)
	mux.HandleFunc("DELETE /books/{id}", s.deleteBook)
}

func (s *apiServer) health(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *apiServer) createBook(w http.ResponseWriter, r *http.Request) {
	var b Book
	if err := decodeJSON(r, &b); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body", err)
		return
	}
	if err := validateBook(&b); err != nil {
		writeError(w, http.StatusBadRequest, err.Error(), nil)
		return
	}
	created, err := createBook(s.db, &b)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to create book", err)
		return
	}
	writeJSON(w, http.StatusCreated, created)
}

func (s *apiServer) listBooks(w http.ResponseWriter, r *http.Request) {
	author := r.URL.Query().Get("author")
	books, err := listBooks(s.db, author)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to list books", err)
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"books": books, "count": len(books)})
}

func (s *apiServer) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	b, err := getBook(s.db, id)
	if err != nil {
		if errors.Is(err, errBookNotFound) {
			writeError(w, http.StatusNotFound, "book not found", nil)
			return
		}
		writeError(w, http.StatusInternalServerError, "failed to fetch book", err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (s *apiServer) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	var b Book
	if err := decodeJSON(r, &b); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body", err)
		return
	}
	if err := validateBook(&b); err != nil {
		writeError(w, http.StatusBadRequest, err.Error(), nil)
		return
	}
	updated, err := updateBook(s.db, id, &b)
	if err != nil {
		if errors.Is(err, errBookNotFound) {
			writeError(w, http.StatusNotFound, "book not found", nil)
			return
		}
		writeError(w, http.StatusInternalServerError, "failed to update book", err)
		return
	}
	writeJSON(w, http.StatusOK, updated)
}

func (s *apiServer) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	if err := deleteBook(s.db, id); err != nil {
		if errors.Is(err, errBookNotFound) {
			writeError(w, http.StatusNotFound, "book not found", nil)
			return
		}
		writeError(w, http.StatusInternalServerError, "failed to delete book", err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	raw := r.PathValue("id")
	id, err := strconv.ParseInt(raw, 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "invalid book id", err)
		return 0, false
	}
	return id, true
}

func decodeJSON(r *http.Request, dst any) error {
	dec := json.NewDecoder(r.Body)
	defer r.Body.Close()
	dec.DisallowUnknownFields()
	if err := dec.Decode(dst); err != nil {
		if strings.Contains(err.Error(), "EOF") {
			return errors.New("request body is empty")
		}
		return err
	}
	return nil
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if v != nil {
		_ = json.NewEncoder(w).Encode(v)
	}
}

func writeError(w http.ResponseWriter, status int, msg string, cause error) {
	resp := map[string]string{"error": msg}
	if cause != nil && msg == "" {
		resp["error"] = cause.Error()
	}
	writeJSON(w, status, resp)
	if cause != nil {
		log.Printf("http %d: %s: %v", status, msg, cause)
	}
}
