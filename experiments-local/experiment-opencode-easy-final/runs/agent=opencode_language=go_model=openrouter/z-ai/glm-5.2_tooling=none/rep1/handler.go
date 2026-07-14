package main

import (
	"encoding/json"
	"errors"
	"io"
	"log"
	"net/http"
	"strconv"
	"strings"
)

type API struct {
	store *Store
	mux   *http.ServeMux
}

func NewAPI(store *Store) *API {
	a := &API{store: store, mux: http.NewServeMux()}
	a.routes()
	return a
}

func (a *API) routes() {
	a.mux.HandleFunc("GET /health", a.health)
	a.mux.HandleFunc("GET /books", a.listBooks)
	a.mux.HandleFunc("POST /books", a.createBook)
	a.mux.HandleFunc("GET /books/{id}", a.getBook)
	a.mux.HandleFunc("PUT /books/{id}", a.updateBook)
	a.mux.HandleFunc("DELETE /books/{id}", a.deleteBook)
}

func (a *API) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	a.mux.ServeHTTP(w, r)
}

func (a *API) health(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (a *API) listBooks(w http.ResponseWriter, r *http.Request) {
	author := r.URL.Query().Get("author")
	books, err := a.store.List(author)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "internal error", err)
		return
	}
	if books == nil {
		books = []*Book{}
	}
	writeJSON(w, http.StatusOK, books)
}

func (a *API) createBook(w http.ResponseWriter, r *http.Request) {
	in, ok := decode(w, r)
	if !ok {
		return
	}
	b, err := validateBook(in)
	if err != nil {
		var ve *ValidationError
		if errors.As(err, &ve) {
			writeJSON(w, http.StatusBadRequest, map[string]any{
				"error":  "validation error",
				"fields": ve.Fields,
			})
			return
		}
		writeError(w, http.StatusInternalServerError, "internal error", err)
		return
	}
	if _, err := a.store.Create(b); err != nil {
		writeError(w, http.StatusInternalServerError, "internal error", err)
		return
	}
	writeJSON(w, http.StatusCreated, b)
}

func (a *API) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	b, err := a.store.Get(id)
	if err != nil {
		if errors.Is(err, ErrNotFound) {
			writeJSON(w, http.StatusNotFound, map[string]string{"error": "book not found"})
			return
		}
		writeError(w, http.StatusInternalServerError, "internal error", err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (a *API) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	in, ok := decode(w, r)
	if !ok {
		return
	}
	b, err := validatePartial(in)
	if err != nil {
		var ve *ValidationError
		if errors.As(err, &ve) {
			writeJSON(w, http.StatusBadRequest, map[string]any{
				"error":  "validation error",
				"fields": ve.Fields,
			})
			return
		}
		writeError(w, http.StatusInternalServerError, "internal error", err)
		return
	}
	updated, err := a.store.Update(id, b)
	if err != nil {
		if errors.Is(err, ErrNotFound) {
			writeJSON(w, http.StatusNotFound, map[string]string{"error": "book not found"})
			return
		}
		writeError(w, http.StatusInternalServerError, "internal error", err)
		return
	}
	writeJSON(w, http.StatusOK, updated)
}

func (a *API) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	if err := a.store.Delete(id); err != nil {
		if errors.Is(err, ErrNotFound) {
			writeJSON(w, http.StatusNotFound, map[string]string{"error": "book not found"})
			return
		}
		writeError(w, http.StatusInternalServerError, "internal error", err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	idStr := r.PathValue("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil || id < 1 {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid id"})
		return 0, false
	}
	return id, true
}

func decode(w http.ResponseWriter, r *http.Request) (bookInput, bool) {
	var in bookInput
	body, err := io.ReadAll(r.Body)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "cannot read body"})
		return in, false
	}
	if strings.TrimSpace(string(body)) == "" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "empty body"})
		return in, false
	}
	if err := json.Unmarshal(body, &in); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid JSON"})
		return in, false
	}
	return in, true
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(v); err != nil {
		log.Printf("write json: %v", err)
	}
}

func writeError(w http.ResponseWriter, status int, msg string, err error) {
	log.Printf("%s: %v", msg, err)
	writeJSON(w, status, map[string]string{"error": msg})
}
