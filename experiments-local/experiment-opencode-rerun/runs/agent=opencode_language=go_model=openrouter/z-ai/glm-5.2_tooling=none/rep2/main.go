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

	if v := os.Getenv("BOOKAPI_ADDR"); v != "" {
		*addr = v
	}
	if v := os.Getenv("BOOKAPI_DB"); v != "" {
		*dbPath = v
	}

	db, err := openDB(*dbPath)
	if err != nil {
		log.Fatalf("db: %v", err)
	}
	defer db.Close()

	mux := http.NewServeMux()
	newAPIServer(db).registerRoutes(mux)

	log.Printf("bookapi listening on %s (db=%s)", *addr, *dbPath)
	srv := &http.Server{Addr: *addr, Handler: mux, ReadHeaderTimeout: 5}
	if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatalf("server: %v", err)
	}
}
