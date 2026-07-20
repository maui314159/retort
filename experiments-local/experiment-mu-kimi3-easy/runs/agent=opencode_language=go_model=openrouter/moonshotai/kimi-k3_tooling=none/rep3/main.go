package main

import (
	"log"
	"net/http"
	"os"
)

func main() {
	port := getenv("PORT", "8080")
	dbPath := getenv("DB_PATH", "books.db")

	store, err := OpenStore(dbPath)
	if err != nil {
		log.Fatalf("open store: %v", err)
	}
	defer store.Close()

	log.Printf("book API listening on :%s (db: %s)", port, dbPath)
	log.Fatal(http.ListenAndServe(":"+port, NewServer(store).Routes()))
}

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
