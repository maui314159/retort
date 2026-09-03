package main

import (
	"database/sql"
	"log"
	"net/http"
	"os"

	"github.com/example/bookapi/handler"
	"github.com/example/bookapi/store"

	_ "modernc.org/sqlite"
)

func main() {
	dbPath := os.Getenv("DB_PATH")
	if dbPath == "" {
		dbPath = "books.db"
	}

	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		log.Fatalf("failed to open database: %v", err)
	}
	defer db.Close()

	if err := store.InitSchema(db); err != nil {
		log.Fatalf("failed to initialize schema: %v", err)
	}

	bookStore := store.NewBookStore(db)
	h := handler.NewHandler(bookStore)

	mux := http.NewServeMux()
	mux.HandleFunc("POST /books", h.CreateBook)
	mux.HandleFunc("GET /books", h.ListBooks)
	mux.HandleFunc("GET /books/{id}", h.GetBook)
	mux.HandleFunc("PUT /books/{id}", h.UpdateBook)
	mux.HandleFunc("DELETE /books/{id}", h.DeleteBook)
	mux.HandleFunc("GET /health", h.Health)

	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = ":8080"
	}

	log.Printf("book API listening on %s", addr)
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
