package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
)

func main() {
	dsn := os.Getenv("DB_PATH")
	if dsn == "" {
		dsn = "books.db"
	}
	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = ":8080"
	}

	repo, err := NewBookRepo(dsn)
	if err != nil {
		log.Fatalf("failed to init db: %v", err)
	}
	defer repo.Close()

	api := NewAPI(repo)
	fmt.Printf("listening on %s\n", addr)
	log.Fatal(http.ListenAndServe(addr, api))
}
