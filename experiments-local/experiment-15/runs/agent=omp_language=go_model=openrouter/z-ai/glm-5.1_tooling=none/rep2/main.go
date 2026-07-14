package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
)

func main() {
	dbPath := os.Getenv("DB_PATH")
	if dbPath == "" {
		dbPath = "books.db"
	}
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	store, err := NewBookStore(dbPath)
	if err != nil {
		log.Fatalf("failed to open database: %v", err)
	}
	defer store.Close()

	api := NewAPI(store)
	addr := fmt.Sprintf(":%s", port)
	log.Printf("listening on %s", addr)
	if err := http.ListenAndServe(addr, api); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
