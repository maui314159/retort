package handlers

import (
	"bookapi/repository"
	"github.com/gorilla/mux"
)

type Handler struct {
	repo repository.BookRepository
}

func NewHandler(repo repository.BookRepository) *Handler {
	return &Handler{repo: repo}
}

func (h *Handler) RegisterRoutes(router *mux.Router) {
	router.HandleFunc("/books", h.CreateBook).Methods("POST")
	router.HandleFunc("/books", h.GetBooks).Methods("GET")
	router.HandleFunc("/books/{id}", h.GetBook).Methods("GET")
	router.HandleFunc("/books/{id}", h.UpdateBook).Methods("PUT")
	router.HandleFunc("/books/{id}", h.DeleteBook).Methods("DELETE")
	router.HandleFunc("/health", h.HealthCheck).Methods("GET")
}