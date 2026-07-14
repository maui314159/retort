package books

import (
	"context"
	"encoding/json"
	"errors"
	"log/slog"
	"net/http"
	"strconv"
	"strings"
)

// Server wires a Store to HTTP handlers. It is safe for concurrent use.
type Server struct {
	store Store
	log   *slog.Logger
}

// NewServer returns a Server that uses the given store. If log is nil,
// slog.Default() is used.
func NewServer(store Store, log *slog.Logger) *Server {
	if log == nil {
		log = slog.Default()
	}
	return &Server{store: store, log: log}
}

// Routes returns a fully-configured *http.ServeMux. Using Go 1.22's
// pattern matching keeps the routing table in one place and avoids a
// third-party router dependency.
func (s *Server) Routes() *http.ServeMux {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", s.handleHealth)
	mux.HandleFunc("GET /books", s.handleList)
	mux.HandleFunc("POST /books", s.handleCreate)
	mux.HandleFunc("GET /books/{id}", s.handleGet)
	mux.HandleFunc("PUT /books/{id}", s.handleUpdate)
	mux.HandleFunc("DELETE /books/{id}", s.handleDelete)
	return mux
}

// --- handlers ---------------------------------------------------------------

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) handleList(w http.ResponseWriter, r *http.Request) {
	author := r.URL.Query().Get("author")
	books, err := s.store.List(r.Context(), author)
	if err != nil {
		s.log.Error("list books", "err", err)
		writeError(w, http.StatusInternalServerError, "internal error")
		return
	}
	// Always emit a JSON array (never null) so clients can iterate
	// without a special case for the empty result.
	if books == nil {
		books = []*Book{}
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *Server) handleCreate(w http.ResponseWriter, r *http.Request) {
	var b Book
	if err := decodeJSON(r, &b); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	if err := b.Validate(); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	if err := s.store.Create(r.Context(), &b); err != nil {
		s.log.Error("create book", "err", err)
		writeError(w, http.StatusInternalServerError, "internal error")
		return
	}
	writeJSON(w, http.StatusCreated, b)
}

func (s *Server) handleGet(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	b, err := s.store.Get(r.Context(), id)
	if err != nil {
		s.writeStoreError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (s *Server) handleUpdate(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	var b Book
	if err := decodeJSON(r, &b); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	if err := b.Validate(); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	if err := s.store.Update(r.Context(), id, &b); err != nil {
		s.writeStoreError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (s *Server) handleDelete(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	if err := s.store.Delete(r.Context(), id); err != nil {
		s.writeStoreError(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// --- helpers ----------------------------------------------------------------

// parseID extracts the {id} path parameter and validates it as int64.
// On failure it writes the appropriate error response and returns ok=false.
func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	raw := r.PathValue("id")
	id, err := strconv.ParseInt(raw, 10, 64)
	if err != nil || id <= 0 {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return 0, false
	}
	return id, true
}

// writeStoreError maps store errors to HTTP responses.
func (s *Server) writeStoreError(w http.ResponseWriter, err error) {
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	s.log.Error("store error", "err", err)
	writeError(w, http.StatusInternalServerError, "internal error")
}

// decodeJSON parses the request body into v and returns a user-friendly
// error for malformed payloads. It also rejects unknown trailing data
// so clients get a clear signal when they POST the wrong shape.
func decodeJSON(r *http.Request, v any) error {
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(v); err != nil {
		if isUnknownFieldErr(err) {
			return errors.New("unknown field in request body")
		}
		return errors.New("invalid JSON body: " + err.Error())
	}
	return nil
}

func isUnknownFieldErr(err error) bool {
	var e *json.UnmarshalTypeError
	if errors.As(err, &e) {
		return false
	}
	// modernc/json surfaces unknown fields via the error string;
	// checking the message keeps the helper decoupled from
	// the specific type name.
	return strings.Contains(err.Error(), "unknown field")
}

// writeJSON marshals v and writes it with the given status code.
func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	enc := json.NewEncoder(w)
	enc.SetEscapeHTML(false)
	if err := enc.Encode(v); err != nil {
		// At this point the status is already sent; log and bail.
		slog.Default().Error("encode response", "err", err)
	}
}

// writeError sends a {"error": "..."} body with the given status.
func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

// requestContext is a thin shim so tests can mint a request context
// without importing net/http/httptest in this file.
func requestContext(r *http.Request) context.Context { return r.Context() }
