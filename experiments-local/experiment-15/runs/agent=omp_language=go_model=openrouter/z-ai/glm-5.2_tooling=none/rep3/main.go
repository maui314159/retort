package main

import (
	"flag"
	"log"
	"net/http"
	"os"
)

func main() {
	addr := flag.String("addr", ":8080", "address to listen on")
	dbPath := flag.String("db", "books.db", "path to the SQLite database file")
	flag.Parse()

	store, err := NewStore(*dbPath)
	if err != nil {
		log.Fatalf("failed to open store: %v", err)
	}
	defer store.Close()

	handler := NewHandler(store).Routes()

	log.Printf("books service listening on %s (db=%s)", *addr, *dbPath)
	srv := &http.Server{Addr: *addr, Handler: handler}
	if err := srv.ListenAndServe(); err != nil {
		log.Printf("server stopped: %v", err)
		os.Exit(1)
	}
}
