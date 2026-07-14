package main

import (
	"flag"
	"log"
	"net/http"
	"os"
)

func main() {
	addr := flag.String("addr", ":8080", "HTTP listen address")
	dbPath := flag.String("db", "books.db", "SQLite database file path")
	flag.Parse()

	store, err := NewStore(*dbPath)
	if err != nil {
		log.Fatalf("failed to open store: %v", err)
	}
	defer store.Close()

	srv := NewServer(store)
	log.Printf("book API listening on %s (db=%s)", *addr, *dbPath)
	if err := http.ListenAndServe(*addr, srv); err != nil {
		log.Printf("server error: %v", err)
		os.Exit(1)
	}
}
