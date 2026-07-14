package main

import (
	"flag"
	"log"
	"net/http"
	"os"
)

func main() {
	addr := flag.String("addr", ":8080", "HTTP listen address")
	dbPath := flag.String("db", "books.db", "SQLite database path")
	flag.Parse()

	store, err := NewStore(*dbPath)
	if err != nil {
		log.Fatalf("init store: %v", err)
	}
	defer store.Close()

	// Ensure file-based DB is removed only when using in-memory ':memory:'
	// (no-op for file paths).
	if *dbPath == ":memory:" {
		defer func() { _ = os.Remove(*dbPath) }()
	}

	api := NewAPI(store)
	log.Printf("book API listening on %s (db=%s)", *addr, *dbPath)
	srv := &http.Server{
		Addr:    *addr,
		Handler: api,
	}
	if err := srv.ListenAndServe(); err != nil {
		log.Fatalf("server: %v", err)
	}
}
