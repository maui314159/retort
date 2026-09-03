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

	handler := NewAPIHandler(store)
	srv := &http.Server{
		Addr:     *addr,
		Handler:  handler.Routes(),
		ErrorLog: log.New(os.Stderr, "server: ", log.LstdFlags),
	}

	log.Printf("listening on %s (db=%s)", *addr, *dbPath)
	if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatalf("server error: %v", err)
	}
}
