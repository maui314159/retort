// Package api exposes the HTTP surface of the book service.
//
// Handlers are bound to a Store so tests can swap in an in-memory SQLite (or
// any future implementation of the same surface). Routing uses the pattern
// matching built into net/http in Go 1.22+, so no third-party router is
// pulled in.
package api

import (
	"context"
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"strconv"
	"strings"

	"books/internal/book"
	"books/internal/store"
)

// API is the HTTP-facing service. It holds the store and an error logger;
// both are settable so tests can supply a no-op logger.
type API struct {
	Store  *store.Store
	Logger *log.Logger
}

// Handler returns an http.Handler with all routes registered.
//
// The mux uses Go 1.22+ pattern syntax so methods and path parameters are
// part of the route, not the handler body. Middleware is added via the
// chaining helpers in this file.
func (a *API) Handler() http.Handler {
	if a.Logger == nil {
		a.Logger = log.Default()
	}
	mux := http.NewServeMux()

	mux.HandleFunc("GET /health", a.health)

	// /books collection routes.
	mux.HandleFunc("GET /books", a.listBooks)
	mux.HandleFunc("POST /books", a.createBook)

	// /books/{id} item routes — the pattern captures `id` as a string.
	mux.HandleFunc("GET /books/{id}", a.getBook)
	mux.HandleFunc("PUT /books/{id}", a.updateBook)
	mux.HandleFunc("DELETE /books/{id}", a.deleteBook)

	return a.recoverMiddleware(a.loggingMiddleware(mux))
}

// ---------- handlers ----------

func (a *API) health(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (a *API) listBooks(w http.ResponseWriter, r *http.Request) {
	author := r.URL.Query().Get("author")
	books, err := a.Store.List(r.Context(), author)
	if err != nil {
		a.serverError(w, err)
		return
	}
	// Always return a JSON array, never null, so clients can iterate without
	// a guard.
	if books == nil {
		books = []book.Book{}
	}
	writeJSON(w, http.StatusOK, books)
}

func (a *API) createBook(w http.ResponseWriter, r *http.Request) {
	var in book.Input
	if err := decodeJSON(r, &in); err != nil {
		a.badRequest(w, err)
		return
	}
	if err := in.Validate(); err != nil {
		a.badRequest(w, err)
		return
	}
	b, err := a.Store.Create(r.Context(), in)
	if err != nil {
		a.serverError(w, err)
		return
	}
	writeJSON(w, http.StatusCreated, b)
}

func (a *API) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := a.parseID(w, r)
	if !ok {
		return
	}
	b, err := a.Store.Get(r.Context(), id)
	if err != nil {
		a.writeStoreError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (a *API) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := a.parseID(w, r)
	if !ok {
		return
	}
	var in book.Input
	if err := decodeJSON(r, &in); err != nil {
		a.badRequest(w, err)
		return
	}
	if err := in.Validate(); err != nil {
		a.badRequest(w, err)
		return
	}
	b, err := a.Store.Update(r.Context(), id, in)
	if err != nil {
		a.writeStoreError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (a *API) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := a.parseID(w, r)
	if !ok {
		return
	}
	if err := a.Store.Delete(r.Context(), id); err != nil {
		a.writeStoreError(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// ---------- helpers ----------

// parseID reads the {id} path parameter and writes a 400 if it is not a
// positive integer. Returns the id and ok=true on success.
func (a *API) parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	raw := r.PathValue("id")
	id, err := strconv.ParseInt(raw, 10, 64)
	if err != nil || id <= 0 {
		a.badRequest(w, errors.New("id must be a positive integer"))
		return 0, false
	}
	return id, true
}

// writeStoreError maps store-layer errors to HTTP responses. NotFound becomes
// 404; anything else is a 500 (the caller has already supplied a well-formed
// input by this point).
func (a *API) writeStoreError(w http.ResponseWriter, err error) {
	if errors.Is(err, store.ErrNotFound) {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "book not found"})
		return
	}
	a.serverError(w, err)
}

func (a *API) badRequest(w http.ResponseWriter, err error) {
	writeJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
}

func (a *API) serverError(w http.ResponseWriter, err error) {
	a.Logger.Printf("server error: %v", err)
	writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "internal server error"})
}

// ---------- json ----------

func writeJSON(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	// Errors writing the response are not actionable: the headers are already
	// committed and the client will see a truncated body. Logging is the
	// best we can do.
	_ = json.NewEncoder(w).Encode(body)
}

func decodeJSON(r *http.Request, dst any) error {
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(dst); err != nil {
		// Wrap the underlying error so the client sees a useful message
		// without leaking internals.
		msg := err.Error()
		// Trim "json: " prefix that encoding/json prepends.
		msg = strings.TrimPrefix(msg, "json: ")
		return errors.New("invalid JSON body: " + msg)
	}
	// Reject trailing data: a single JSON document per request.
	if dec.More() {
		return errors.New("invalid JSON body: unexpected trailing data")
	}
	return nil
}

// ---------- middleware ----------

// loggingMiddleware logs each request with method, path, and status code.
// The status is captured via a ResponseWriter wrapper.
func (a *API) loggingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		rw := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
		next.ServeHTTP(rw, r)
		a.Logger.Printf("%s %s -> %d", r.Method, r.URL.Path, rw.status)
	})
}

// recoverMiddleware turns a panicking handler into a 500 instead of
// dropping the connection. The API surface is small but the cost of the
// guard is too.
func (a *API) recoverMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if rec := recover(); rec != nil {
				a.Logger.Printf("panic: %v", rec)
				// Header may already be written; best effort.
				writeJSON(w, http.StatusInternalServerError, map[string]string{
					"error": "internal server error",
				})
			}
		}()
		next.ServeHTTP(w, r)
	})
}

// statusRecorder captures the status code written to the response so the
// logging middleware can include it.
type statusRecorder struct {
	http.ResponseWriter
	status      int
	wroteHeader bool
}

func (s *statusRecorder) WriteHeader(code int) {
	if s.wroteHeader {
		return
	}
	s.status = code
	s.wroteHeader = true
	s.ResponseWriter.WriteHeader(code)
}

func (s *statusRecorder) Write(b []byte) (int, error) {
	if !s.wroteHeader {
		s.wroteHeader = true
	}
	return s.ResponseWriter.Write(b)
}

// Flush forwards Flush so handlers that stream still cooperate with
// http.ResponseController wrappers.
func (s *statusRecorder) Flush() {
	if f, ok := s.ResponseWriter.(http.Flusher); ok {
		f.Flush()
	}
}

// Unwrap exposes the underlying ResponseWriter for http.ResponseController
// and any code that wants to inspect headers.
func (s *statusRecorder) Unwrap() http.ResponseWriter { return s.ResponseWriter }

// Compile-time check that context is used (avoid import-only lint noise).
var _ = context.Background
