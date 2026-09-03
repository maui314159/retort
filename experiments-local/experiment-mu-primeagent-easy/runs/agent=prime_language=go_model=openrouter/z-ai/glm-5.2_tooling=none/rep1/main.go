package main

import (
	"flag"
	"log"
	"net/http"
	"os"
)

func main() {
	addr := flag.String("addr", envOr("ADDR", ":8080"), "address to listen on")
	dbPath := flag.String("db", envOr("DB_PATH", "books.db"), "path to the SQLite database file")
	flag.Parse()

	store, err := NewStore(*dbPath)
	if err != nil {
		log.Fatalf("failed to open store: %v", err)
	}
	defer store.Close()

	h := NewHandler(store)
	srv := &http.Server{
		Addr:    *addr,
		Handler: h.Routes(),
	}

	log.Printf("book API listening on %s (db=%s)", *addr, *dbPath)
	if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatalf("server error: %v", err)
	}
}

// envOr returns the environment variable value or fallback if unset.
func envOr(key, fallback string) string {
	if v, ok := os.LookupEnv(key); ok {
		return v
	}
	return fallback
}
