package main

import (
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
)

func main() {
	addr := flag.String("addr", ":8080", "address to listen on")
	dbPath := flag.String("db", "books.db", "path to the SQLite database file")
	flag.Parse()

	// Allow override via environment variables for container/CI use.
	if v := os.Getenv("BOOKAPI_ADDR"); v != "" {
		*addr = v
	}
	if v := os.Getenv("BOOKAPI_DB"); v != "" {
		*dbPath = v
	}

	store, err := NewStore(*dbPath)
	if err != nil {
		log.Fatalf("failed to open store: %v", err)
	}
	defer store.Close()

	api := NewAPI(store)
	srv := &http.Server{
		Addr:    *addr,
		Handler: api.Handler(),
	}

	fmt.Printf("book API listening on %s (db=%s)\n", *addr, *dbPath)
	if err := srv.ListenAndServe(); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
