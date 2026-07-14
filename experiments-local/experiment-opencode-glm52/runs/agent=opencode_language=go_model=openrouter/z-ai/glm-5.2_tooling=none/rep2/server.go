package main

import (
	"database/sql"
	"net/http"
	"strings"
)

// server holds the application's shared dependencies.
type server struct {
	db *sql.DB
}

// newServer opens the database at the given path and returns a ready server.
func newServer(dbPath string) (*server, error) {
	db, err := openDB(dbPath)
	if err != nil {
		return nil, err
	}
	return &server{db: db}, nil
}

// routes wires the HTTP mux. It is split out so tests can reuse it.
func (s *server) routes() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			writeError(w, http.StatusMethodNotAllowed, "method not allowed")
			return
		}
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})
	mux.HandleFunc("/books", s.booksHandler)
	mux.HandleFunc("/books/", s.bookHandler)
	return logging(mux)
}

// logging is a minimal request logger middleware.
func logging(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		next.ServeHTTP(w, r)
	})
}

// matchesPath reports whether a request path matches /books/{id} shape.
// (Kept simple; only used to clarify intent in the package.)
func matchesPath(path, prefix string) bool {
	return strings.HasPrefix(path, prefix)
}
