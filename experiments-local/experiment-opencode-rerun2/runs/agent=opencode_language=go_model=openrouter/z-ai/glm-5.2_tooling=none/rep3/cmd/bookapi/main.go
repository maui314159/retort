package main

import (
	"flag"
	"log"
	"net/http"
	"os"

	"bookapi/internal/handlers"
	"bookapi/internal/store"
)

func main() {
	addr := flag.String("addr", ":8080", "HTTP listen address")
	dbPath := flag.String("db", "books.db", "SQLite database path")
	flag.Parse()

	if v := os.Getenv("ADDR"); v != "" {
		*addr = v
	}
	if v := os.Getenv("DB_PATH"); v != "" {
		*dbPath = v
	}

	s, err := store.Open(*dbPath)
	if err != nil {
		log.Fatalf("open store: %v", err)
	}
	defer s.Close()

	h := handlers.New(s)
	log.Printf("bookapi listening on %s (db=%s)", *addr, *dbPath)
	if err := http.ListenAndServe(*addr, h.Routes()); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
