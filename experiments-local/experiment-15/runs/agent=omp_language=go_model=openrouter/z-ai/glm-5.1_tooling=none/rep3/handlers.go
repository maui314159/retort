package main

import (
	"encoding/json"
	"net/http"
	"strconv"
	"time"

	"github.com/go-chi/chi/v5"
)

type Server struct {
	router *chi.Mux
	store  *BookStore
}

func NewServer(store *BookStore) *Server {
	s := &Server{store: store}
	r := chi.NewRouter()

	r.Get("/health", s.handleHealth)
	r.Post("/books", s.handleCreateBook)
	r.Get("/books", s.handleListBooks)
	r.Get("/books/{id}", s.handleGetBook)
	r.Put("/books/{id}", s.handleUpdateBook)
	r.Delete("/books/{id}", s.handleDeleteBook)

	s.router = r
	return s
}

func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	s.router.ServeHTTP(w, r)
}

func writeJSON(w http.ResponseWriter, status int, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, ErrorResponse{Error: msg})
}

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) handleCreateBook(w http.ResponseWriter, r *http.Request) {
	var input BookInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	if input.Title == "" {
		writeError(w, http.StatusBadRequest, "title is required")
		return
	}
	if input.Author == "" {
		writeError(w, http.StatusBadRequest, "author is required")
		return
	}

	now := time.Now().UTC().Format(time.RFC3339)
	book := Book{
		Title:     input.Title,
		Author:    input.Author,
		Year:      input.Year,
		ISBN:      input.ISBN,
		CreatedAt: now,
		UpdatedAt: now,
	}

	if err := s.store.Create(&book); err != nil {
		writeError(w, http.StatusInternalServerError, "failed to create book")
		return
	}

	writeJSON(w, http.StatusCreated, book)
}

func (s *Server) handleListBooks(w http.ResponseWriter, r *http.Request) {
	author := r.URL.Query().Get("author")
	books, err := s.store.List(author)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to list books")
		return
	}
	if books == nil {
		books = []Book{}
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *Server) handleGetBook(w http.ResponseWriter, r *http.Request) {
	id, err := strconv.ParseInt(chi.URLParam(r, "id"), 10, 64)
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return
	}

	book, err := s.store.Get(id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to get book")
		return
	}
	if book == nil {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}

	writeJSON(w, http.StatusOK, book)
}

func (s *Server) handleUpdateBook(w http.ResponseWriter, r *http.Request) {
	id, err := strconv.ParseInt(chi.URLParam(r, "id"), 10, 64)
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return
	}

	var input BookInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	if input.Title == "" {
		writeError(w, http.StatusBadRequest, "title is required")
		return
	}
	if input.Author == "" {
		writeError(w, http.StatusBadRequest, "author is required")
		return
	}

	existing, err := s.store.Get(id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to get book")
		return
	}
	if existing == nil {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}

	existing.Title = input.Title
	existing.Author = input.Author
	existing.Year = input.Year
	existing.ISBN = input.ISBN
	existing.UpdatedAt = time.Now().UTC().Format(time.RFC3339)

	updated, err := s.store.Update(id, existing)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to update book")
		return
	}
	if !updated {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}

	writeJSON(w, http.StatusOK, existing)
}

func (s *Server) handleDeleteBook(w http.ResponseWriter, r *http.Request) {
	id, err := strconv.ParseInt(chi.URLParam(r, "id"), 10, 64)
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return
	}

	deleted, err := s.store.Delete(id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to delete book")
		return
	}
	if !deleted {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}

	w.WriteHeader(http.StatusNoContent)
}
