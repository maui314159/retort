package handlers

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"

	"bookapi/database"
	"bookapi/models"

	"github.com/go-chi/chi/v5"
	"github.com/go-playground/validator/v10"
)

var (
	db        *sql.DB
	store     models.BookStore
	validate  *validator.Validate
)

func InitHandlers() error {
	var err error
	db, err = database.InitDB()
	if err != nil {
		return fmt.Errorf("failed to initialize database: %w", err)
	}
	store = database.NewBookStore(db)
	validate = validator.New()
	return nil
}

func SetStore(s models.BookStore) {
	store = s
}

// TestSetup initializes store and validator for tests
func TestSetup(s models.BookStore) {
	store = s
	validate = validator.New()
}

func HealthCheck(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}

func CreateBook(w http.ResponseWriter, r *http.Request) {
	var req models.BookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, `{"error": "Invalid request body"}`, http.StatusBadRequest)
		return
	}

	// Validate input
	if err := validate.Struct(req); err != nil {
		errors := []string{}
		for _, err := range err.(validator.ValidationErrors) {
			errors = append(errors, fmt.Sprintf("%s is %s", err.Field(), err.Tag()))
		}
		response := map[string]interface{}{
			"error":   "Validation failed",
			"details": errors,
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(response)
		return
	}

	book, err := store.Create(&req)
	if err != nil {
		if strings.Contains(err.Error(), "title and author are required") {
			http.Error(w, `{"error": "Title and author are required"}`, http.StatusBadRequest)
			return
		}
		http.Error(w, fmt.Sprintf(`{"error": "%s"}`, err.Error()), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(book)
}

func ListBooks(w http.ResponseWriter, r *http.Request) {
	authorFilter := r.URL.Query().Get("author")

	books, err := store.List(authorFilter)
	if err != nil {
		http.Error(w, fmt.Sprintf(`{"error": "%s"}`, err.Error()), http.StatusInternalServerError)
		return
	}

	if books == nil {
		books = []models.Book{}
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(books)
}

func GetBook(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")

	book, err := store.GetByID(id)
	if err != nil {
		if err.Error() == "book not found" {
			http.Error(w, `{"error": "Book not found"}`, http.StatusNotFound)
			return
		}
		http.Error(w, fmt.Sprintf(`{"error": "%s"}`, err.Error()), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(book)
}

func UpdateBook(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")

	var req models.BookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, `{"error": "Invalid request body"}`, http.StatusBadRequest)
		return
	}

	// Validate input
	if err := validate.Struct(req); err != nil {
		errors := []string{}
		for _, err := range err.(validator.ValidationErrors) {
			errors = append(errors, fmt.Sprintf("%s is %s", err.Field(), err.Tag()))
		}
		response := map[string]interface{}{
			"error":   "Validation failed",
			"details": errors,
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(response)
		return
	}

	book, err := store.Update(id, &req)
	if err != nil {
		if err.Error() == "book not found" {
			http.Error(w, `{"error": "Book not found"}`, http.StatusNotFound)
			return
		}
		if strings.Contains(err.Error(), "title and author are required") {
			http.Error(w, `{"error": "Title and author are required"}`, http.StatusBadRequest)
			return
		}
		http.Error(w, fmt.Sprintf(`{"error": "%s"}`, err.Error()), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(book)
}

func DeleteBook(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")

	err := store.Delete(id)
	if err != nil {
		if err.Error() == "book not found" {
			http.Error(w, `{"error": "Book not found"}`, http.StatusNotFound)
			return
		}
		http.Error(w, fmt.Sprintf(`{"error": "%s"}`, err.Error()), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusNoContent)
}