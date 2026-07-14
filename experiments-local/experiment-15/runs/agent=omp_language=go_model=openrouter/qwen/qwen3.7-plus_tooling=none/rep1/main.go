package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"strings"

	_ "modernc.org/sqlite"
)

type Book struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year,omitempty"`
	ISBN   string `json:"isbn,omitempty"`
}

type BookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type App struct {
	DB *sql.DB
}

func (a *App) InitDB() error {
	createTableSQL := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT
	);`
	_, err := a.DB.Exec(createTableSQL)
	return err
}

func respondJSON(w http.ResponseWriter, status int, payload interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if payload != nil {
		json.NewEncoder(w).Encode(payload)
	}
}

func respondError(w http.ResponseWriter, code int, message string) {
	respondJSON(w, code, map[string]string{"error": message})
}

func (a *App) healthHandler(w http.ResponseWriter, r *http.Request) {
	respondJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (a *App) createBookHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		respondError(w, http.StatusMethodNotAllowed, "Method not allowed")
		return
	}

	var input BookInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		respondError(w, http.StatusBadRequest, "Invalid JSON")
		return
	}

	if strings.TrimSpace(input.Title) == "" || strings.TrimSpace(input.Author) == "" {
		respondError(w, http.StatusBadRequest, "Title and author are required")
		return
	}

	result, err := a.DB.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		input.Title, input.Author, input.Year, input.ISBN)
	if err != nil {
		respondError(w, http.StatusInternalServerError, "Failed to create book")
		return
	}

	id, _ := result.LastInsertId()
	respondJSON(w, http.StatusCreated, Book{
		ID:     int(id),
		Title:  input.Title,
		Author: input.Author,
		Year:   input.Year,
		ISBN:   input.ISBN,
	})
}

func (a *App) getBooksHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		respondError(w, http.StatusMethodNotAllowed, "Method not allowed")
		return
	}

	authorFilter := r.URL.Query().Get("author")
	var rows *sql.Rows
	var err error

	if authorFilter != "" {
		rows, err = a.DB.Query("SELECT id, title, author, year, isbn FROM books WHERE author LIKE ?", "%"+authorFilter+"%")
	} else {
		rows, err = a.DB.Query("SELECT id, title, author, year, isbn FROM books")
	}

	if err != nil {
		respondError(w, http.StatusInternalServerError, "Failed to fetch books")
		return
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			respondError(w, http.StatusInternalServerError, "Failed to scan book")
			return
		}
		books = append(books, b)
	}

	if books == nil {
		books = []Book{}
	}
	respondJSON(w, http.StatusOK, books)
}

func (a *App) getBookHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		respondError(w, http.StatusMethodNotAllowed, "Method not allowed")
		return
	}

	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		respondError(w, http.StatusBadRequest, "Invalid book ID")
		return
	}

	var b Book
	err = a.DB.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if err == sql.ErrNoRows {
		respondError(w, http.StatusNotFound, "Book not found")
		return
	} else if err != nil {
		respondError(w, http.StatusInternalServerError, "Failed to fetch book")
		return
	}

	respondJSON(w, http.StatusOK, b)
}

func (a *App) updateBookHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPut {
		respondError(w, http.StatusMethodNotAllowed, "Method not allowed")
		return
	}

	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		respondError(w, http.StatusBadRequest, "Invalid book ID")
		return
	}

	var input BookInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		respondError(w, http.StatusBadRequest, "Invalid JSON")
		return
	}

	if strings.TrimSpace(input.Title) == "" || strings.TrimSpace(input.Author) == "" {
		respondError(w, http.StatusBadRequest, "Title and author are required")
		return
	}

	var existingTitle, existingAuthor string
	var existingYear sql.NullInt64
	var existingISBN sql.NullString
	err = a.DB.QueryRow("SELECT title, author, year, isbn FROM books WHERE id = ?", id).Scan(&existingTitle, &existingAuthor, &existingYear, &existingISBN)
	if err == sql.ErrNoRows {
		respondError(w, http.StatusNotFound, "Book not found")
		return
	} else if err != nil {
		respondError(w, http.StatusInternalServerError, "Failed to fetch book")
		return
	}

	year := input.Year
	isbn := input.ISBN

	_, err = a.DB.Exec("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
		input.Title, input.Author, year, isbn, id)
	if err != nil {
		respondError(w, http.StatusInternalServerError, "Failed to update book")
		return
	}

	respondJSON(w, http.StatusOK, Book{
		ID:     id,
		Title:  input.Title,
		Author: input.Author,
		Year:   year,
		ISBN:   isbn,
	})
}

func (a *App) deleteBookHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodDelete {
		respondError(w, http.StatusMethodNotAllowed, "Method not allowed")
		return
	}

	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		respondError(w, http.StatusBadRequest, "Invalid book ID")
		return
	}

	res, err := a.DB.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		respondError(w, http.StatusInternalServerError, "Failed to delete book")
		return
	}

	rowsAffected, _ := res.RowsAffected()
	if rowsAffected == 0 {
		respondError(w, http.StatusNotFound, "Book not found")
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

func (a *App) Routes() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", a.healthHandler)
	mux.HandleFunc("POST /books", a.createBookHandler)
	mux.HandleFunc("GET /books", a.getBooksHandler)
	mux.HandleFunc("GET /books/{id}", a.getBookHandler)
	mux.HandleFunc("PUT /books/{id}", a.updateBookHandler)
	mux.HandleFunc("DELETE /books/{id}", a.deleteBookHandler)
	return mux
}

func main() {
	db, err := sql.Open("sqlite", "books.db")
	if err != nil {
		log.Fatalf("Failed to open database: %v", err)
	}
	defer db.Close()

	app := &App{DB: db}
	if err := app.InitDB(); err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}

	fmt.Println("Server starting on :8080")
	log.Fatal(http.ListenAndServe(":8080", app.Routes()))
}
