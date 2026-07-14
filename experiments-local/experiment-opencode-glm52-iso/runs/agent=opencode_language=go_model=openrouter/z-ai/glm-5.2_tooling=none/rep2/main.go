package main

import (
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
)

func main() {
	addr := flag.String("addr", ":8080", "HTTP listen address")
	dbPath := flag.String("db", "books.db", "SQLite database file path")
	flag.Parse()

	store, err := NewStorage(*dbPath, false)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to open storage: %v\n", err)
		os.Exit(1)
	}
	defer store.Close()

	api := NewAPI(store)
	srv := &http.Server{
		Addr:    *addr,
		Handler: api.Routes(),
	}

	log.Printf("book API listening on %s (db=%s)", *addr, *dbPath)
	if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatalf("server error: %v", err)
	}
}
