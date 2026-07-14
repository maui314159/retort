package main

import (
	"log"
	"net/http"
	"os"

	"bookapi/handlers"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
)

func main() {
	// Initialize handlers
	err := handlers.InitHandlers()
	if err != nil {
		log.Fatal("Failed to initialize handlers:", err)
	}

	// Set up router
	r := chi.NewRouter()
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)

	// Health check
	r.Get("/health", handlers.HealthCheck)

	// Book routes
	r.Route("/books", func(r chi.Router) {
		r.Post("/", handlers.CreateBook)
		r.Get("/", handlers.ListBooks)
		r.Route("/{id}", func(r chi.Router) {
			r.Get("/", handlers.GetBook)
			r.Put("/", handlers.UpdateBook)
			r.Delete("/", handlers.DeleteBook)
		})
	})

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	log.Printf("Server starting on :%s", port)
	log.Fatal(http.ListenAndServe(":"+port, r))
}