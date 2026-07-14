package main

import (
	"bookapi/database"
	"bookapi/handlers"
	"bookapi/repository"
	"log"
	"net/http"

	"github.com/gorilla/mux"
)

func main() {
	db, err := database.InitDB()
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	repo := repository.NewSQLiteBookRepository(db)
	handler := handlers.NewHandler(repo)

	router := setupRouter(handler)

	log.Println("Starting server on :8080")
	if err := http.ListenAndServe(":8080", router); err != nil {
		log.Fatal(err)
	}
}

func setupRouter(handler *handlers.Handler) *mux.Router {
	r := mux.NewRouter()
	handler.RegisterRoutes(r)
	return r
}