package handlers

import (
	"encoding/json"
	"net/http"
	"strconv"

	"bookapi/internal/db"
	"bookapi/internal/models"

	"github.com/gorilla/mux"
)

func respondWithError(w http.ResponseWriter, code int, message string) {
	respondWithJSON(w, code, map[string]string{"error": message})
}

func respondWithJSON(w http.ResponseWriter, code int, payload interface{}) {
	response, _ := json.Marshal(payload)
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	w.Write(response)
}

func validateBook(book *models.Book) error {
	if book.Title == "" {
		return &ValidationError{Field: "title", Message: "title is required"}
	}
	if book.Author == "" {
		return &ValidationError{Field: "author", Message: "author is required"}
	}
	return nil
}

type ValidationError struct {
	Field   string
	Message string
}

func (e *ValidationError) Error() string {
	return e.Message
}

func GetBooksHandler(w http.ResponseWriter, r *http.Request) {
	authorFilter := r.URL.Query().Get("author")
	books, err := db.GetAllBooks(authorFilter)
	if err != nil {
		respondWithError(w, http.StatusInternalServerError, "Failed to fetch books")
		return
	}
	respondWithJSON(w, http.StatusOK, books)
}

func GetBookHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id, err := strconv.Atoi(vars["id"])
	if err != nil {
		respondWithError(w, http.StatusBadRequest, "Invalid book ID")
		return
	}

	book, err := db.GetBookByID(id)
	if err != nil {
		respondWithError(w, http.StatusInternalServerError, "Failed to fetch book")
		return
	}
	if book == nil {
		respondWithError(w, http.StatusNotFound, "Book not found")
		return
	}

	respondWithJSON(w, http.StatusOK, book)
}

func CreateBookHandler(w http.ResponseWriter, r *http.Request) {
	var book models.Book
	decoder := json.NewDecoder(r.Body)
	if err := decoder.Decode(&book); err != nil {
		respondWithError(w, http.StatusBadRequest, "Invalid request payload")
		return
	}
	defer r.Body.Close()

	if err := validateBook(&book); err != nil {
		respondWithError(w, http.StatusBadRequest, err.Error())
		return
	}

	if err := db.CreateBook(&book); err != nil {
		respondWithError(w, http.StatusInternalServerError, "Failed to create book")
		return
	}

	respondWithJSON(w, http.StatusCreated, book)
}

func UpdateBookHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id, err := strconv.Atoi(vars["id"])
	if err != nil {
		respondWithError(w, http.StatusBadRequest, "Invalid book ID")
		return
	}

	var book models.Book
	decoder := json.NewDecoder(r.Body)
	if err := decoder.Decode(&book); err != nil {
		respondWithError(w, http.StatusBadRequest, "Invalid request payload")
		return
	}
	defer r.Body.Close()

	if err := validateBook(&book); err != nil {
		respondWithError(w, http.StatusBadRequest, err.Error())
		return
	}

	err = db.UpdateBook(id, &book)
	if err != nil {
		if err.Error() == "sql: no rows in result set" {
			respondWithError(w, http.StatusNotFound, "Book not found")
			return
		}
		respondWithError(w, http.StatusInternalServerError, "Failed to update book")
		return
	}

	book.ID = id
	respondWithJSON(w, http.StatusOK, book)
}

func DeleteBookHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id, err := strconv.Atoi(vars["id"])
	if err != nil {
		respondWithError(w, http.StatusBadRequest, "Invalid book ID")
		return
	}

	err = db.DeleteBook(id)
	if err != nil {
		if err.Error() == "sql: no rows in result set" {
			respondWithError(w, http.StatusNotFound, "Book not found")
			return
		}
		respondWithError(w, http.StatusInternalServerError, "Failed to delete book")
		return
	}

	respondWithJSON(w, http.StatusOK, map[string]string{"message": "Book deleted successfully"})
}