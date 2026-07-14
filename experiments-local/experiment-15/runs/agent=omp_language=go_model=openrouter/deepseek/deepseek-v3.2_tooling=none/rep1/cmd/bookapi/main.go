package main

import (
	"fmt"
	"log"
	"net/http"

	"bookapi/internal/db"
	"bookapi/internal/handlers"
	"bookapi/internal/health"

	"github.com/gorilla/mux"
)

func main() {
	// Initialize database
	if err := db.InitDB(); err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}

	// Create router
	r := mux.NewRouter()

	// API routes
	r.HandleFunc("/books", handlers.GetBooksHandler).Methods("GET")
	r.HandleFunc("/books", handlers.CreateBookHandler).Methods("POST")
	r.HandleFunc("/books/{id}", handlers.GetBookHandler).Methods("GET")
	r.HandleFunc("/books/{id}", handlers.UpdateBookHandler).Methods("PUT")
	r.HandleFunc("/books/{id}", handlers.DeleteBookHandler).Methods("DELETE")

	// Health check
	r.HandleFunc("/health", health.HealthHandler).Methods("GET")

	// Start server
	port := ":8080"
	fmt.Printf("Server starting on port %s\n", port)
	fmt.Println("Available endpoints:")
	fmt.Println("  GET    /books")
	fmt.Println("  POST   /books")
	fmt.Println("  GET    /books/{id}")
	fmt.Println("  PUT    /books/{id}")
	fmt.Println("  DELETE /books/{id}")
	fmt.Println("  GET    /health")

	log.Fatal(http.ListenAndServe(port, r))
}