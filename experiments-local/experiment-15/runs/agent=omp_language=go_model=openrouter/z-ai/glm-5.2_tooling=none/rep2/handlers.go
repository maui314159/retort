package main

import (
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"net/url"
	"strconv"
	"strings"
)

// API wires the store to HTTP handlers. It holds no mutable state.
type API struct {
	store *Store
}

// newAPI constructs an API backed by the given store.
func newAPI(s *Store) *API {
	return &API{store: s}
}

// routes registers every endpoint on the given mux. Using Go 1.22+ method-
// pattern routing, so each pattern is method-scoped.
func (a *API) routes(mux *http.ServeMux) {
	mux.HandleFunc("GET /health", a.health)
	mux.HandleFunc("POST /books", a.createBook)
	mux.HandleFunc("GET /books", a.listBooks)
	mux.HandleFunc("GET /books/{id}", a.getBook)
	mux.HandleFunc("PUT /books/{id}", a.updateBook)
	mux.HandleFunc("DELETE /books/{id}", a.deleteBook)
}

// health is the liveness/readiness probe.
func (a *API) health(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

// createBook handles POST /books.
func (a *API) createBook(w http.ResponseWriter, r *http.Request) {
	var b Book
	if err := decodeBook(r, &b); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	if err := b.validate(); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	saved, err := a.store.Create(r.Context(), b)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusCreated, saved)
}

// listBooks handles GET /books, honoring an optional ?author= filter.
func (a *API) listBooks(w http.ResponseWriter, r *http.Request) {
	author, _ := url.QueryUnescape(strings.TrimSpace(r.URL.Query().Get("author")))
	books, err := a.store.List(r.Context(), author)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if books == nil {
		books = []Book{}
	}
	writeJSON(w, http.StatusOK, books)
}

// getBook handles GET /books/{id}.
func (a *API) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	b, err := a.store.Get(r.Context(), id)
	if err != nil {
		if errors.Is(err, ErrNotFound) {
			writeError(w, http.StatusNotFound, err.Error())
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, b)
}

// updateBook handles PUT /books/{id}.
func (a *API) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	var b Book
	if err := decodeBook(r, &b); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	if err := b.validate(); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	updated, err := a.store.Update(r.Context(), id, b)
	if err != nil {
		if errors.Is(err, ErrNotFound) {
			writeError(w, http.StatusNotFound, err.Error())
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, updated)
}

// deleteBook handles DELETE /books/{id}.
func (a *API) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	if err := a.store.Delete(r.Context(), id); err != nil {
		if errors.Is(err, ErrNotFound) {
			writeError(w, http.StatusNotFound, err.Error())
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// decodeBook parses the request body as a Book, rejecting unknown fields and
// non-JSON bodies.
func decodeBook(r *http.Request, b *Book) error {
	dec := json.NewDecoder(r.Body)
	defer r.Body.Close()
	dec.DisallowUnknownFields()
	if err := dec.Decode(b); err != nil {
		return err
	}
	return nil
}

// parseID extracts the {id} path value, writing a 400 response on failure.
// The bool result tells the caller whether parsing succeeded.
func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	idStr := r.PathValue("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil || id <= 0 {
		writeError(w, http.StatusBadRequest, "id must be a positive integer")
		return 0, false
	}
	return id, true
}

// writeJSON serializes v as JSON with the given status code.
func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(v); err != nil {
		log.Printf("encode response: %v", err)
	}
}

// writeError emits a structured JSON error envelope.
func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}
