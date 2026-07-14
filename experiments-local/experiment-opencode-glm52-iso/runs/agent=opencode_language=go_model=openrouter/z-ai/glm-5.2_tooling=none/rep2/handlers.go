package main

import (
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"strconv"
	"strings"
)

// API wires HTTP routes to the storage layer.
type API struct {
	store *Storage
}

// NewAPI constructs an API with the given storage.
func NewAPI(store *Storage) *API {
	return &API{store: store}
}

// Routes returns the configured HTTP mux.
func (a *API) Routes() http.Handler {
	mux := http.NewServeMux()

	mux.HandleFunc("GET /health", a.health)
	mux.HandleFunc("POST /books", a.createBook)
	mux.HandleFunc("GET /books", a.listBooks)
	mux.HandleFunc("GET /books/{id}", a.getBook)
	mux.HandleFunc("PUT /books/{id}", a.updateBook)
	mux.HandleFunc("DELETE /books/{id}", a.deleteBook)

	return mux
}

func (a *API) health(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (a *API) createBook(w http.ResponseWriter, r *http.Request) {
	var in bookInput
	if err := decodeJSON(r, &in); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body: "+err.Error())
		return
	}
	if msg := in.validate(); msg != "" {
		writeError(w, http.StatusBadRequest, msg)
		return
	}

	book := &Book{
		Title:  trimSpaces(*in.Title),
		Author: trimSpaces(*in.Author),
		Year:   0,
		ISBN:   "",
	}
	if in.Year != nil {
		book.Year = *in.Year
	}
	if in.ISBN != nil {
		book.ISBN = trimSpaces(*in.ISBN)
	}

	created, err := a.store.CreateBook(book)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not create book: "+err.Error())
		return
	}
	writeJSON(w, http.StatusCreated, created)
}

func (a *API) listBooks(w http.ResponseWriter, r *http.Request) {
	author := strings.TrimSpace(r.URL.Query().Get("author"))
	books, err := a.store.ListBooks(author)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not list books: "+err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"books": books})
}

func (a *API) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	book, err := a.store.GetBook(id)
	if err != nil {
		if errors.Is(err, errNotFound) || strings.Contains(err.Error(), "no rows") {
			writeError(w, http.StatusNotFound, "book not found")
			return
		}
		writeError(w, http.StatusInternalServerError, "could not get book: "+err.Error())
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (a *API) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	var in bookInput
	if err := decodeJSON(r, &in); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body: "+err.Error())
		return
	}

	updated, err := a.store.UpdateBook(id, &in)
	if err != nil {
		if strings.Contains(err.Error(), "no rows") {
			writeError(w, http.StatusNotFound, "book not found")
			return
		}
		writeError(w, http.StatusInternalServerError, "could not update book: "+err.Error())
		return
	}
	writeJSON(w, http.StatusOK, updated)
}

func (a *API) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	deleted, err := a.store.DeleteBook(id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not delete book: "+err.Error())
		return
	}
	if !deleted {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// errNotFound is a sentinel for missing rows, used in tests.
var errNotFound = errors.New("not found")

func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	raw := r.PathValue("id")
	id, err := strconv.ParseInt(raw, 10, 64)
	if err != nil || id <= 0 {
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

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(payload); err != nil {
		log.Printf("encode response: %v", err)
	}
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}
