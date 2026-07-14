package main

import (
	"log"
	"net/http"
)

func main() {
	store, err := NewBookStore("books.db")
	if err != nil {
		log.Fatalf("Failed to open database: %v", err)
	}
	defer store.Close()

	srv := NewServer(store)
	log.Println("Starting server on :8080")
	if err := http.ListenAndServe(":8080", srv); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}
