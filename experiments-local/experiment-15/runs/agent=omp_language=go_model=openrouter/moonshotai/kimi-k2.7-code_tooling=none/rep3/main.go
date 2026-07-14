package main

import (
	"log"
	"net/http"
)

func main() {
	db, err := openDB("books.db")
	if err != nil {
		log.Fatalf("open db: %v", err)
	}
	defer db.Close()

	if err := migrate(db); err != nil {
		log.Fatalf("migrate: %v", err)
	}

	srv := newServer(db)
	log.Println("Server listening on :8080")
	if err := http.ListenAndServe(":8080", srv.router()); err != nil {
		log.Fatalf("listen: %v", err)
	}
}
