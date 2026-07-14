package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"strings"

	_ "modernc.org/sqlite"
)

// Book represents a book in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year,omitempty"`
	ISBN   string `json:"isbn,omitempty"`
}

type server struct {
	db *sql.DB
}

func main() {
	db, err := sql.Open("sqlite", "books.db")
	if err != nil {
		log.Fatalf("open database: %v", err)
	}
	defer db.Close()

	if err := migrate(db); err != nil {
		log.Fatalf("migrate database: %v", err)
	}

	srv := &server{db: db}
	log.Println("Server listening on :8080")
	log.Fatal(http.ListenAndServe(":8080", srv.routes()))
}

func migrate(db *sql.DB) error {
	_, err := db.Exec(`
		CREATE TABLE IF NOT EXISTS books (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			title TEXT NOT NULL,
			author TEXT NOT NULL,
			year INTEGER,
			isbn TEXT
		)
	`)
	return err
}

func (s *server) routes() *http.ServeMux {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", s.healthHandler)
	mux.HandleFunc("POST /books", s.createBook)
	mux.HandleFunc("GET /books", s.listBooks)
	mux.HandleFunc("GET /books/{id}", s.getBook)
	mux.HandleFunc("PUT /books/{id}", s.updateBook)
	mux.HandleFunc("DELETE /books/{id}", s.deleteBook)
	return mux
}

func (s *server) healthHandler(w http.ResponseWriter, r *http.Request) {
	respondJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *server) createBook(w http.ResponseWriter, r *http.Request) {
	var book Book
	if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
		respondError(w, http.StatusBadRequest, "invalid JSON")
		return
	}

	if err := validateBook(&book); err != nil {
		respondError(w, http.StatusBadRequest, err.Error())
		return
	}

	result, err := s.db.Exec(
		"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		book.Title, book.Author, book.Year, book.ISBN,
	)
	if err != nil {
		respondError(w, http.StatusInternalServerError, "database error")
		return
	}

	book.ID, _ = result.LastInsertId()
	respondJSON(w, http.StatusCreated, book)
}

func (s *server) listBooks(w http.ResponseWriter, r *http.Request) {
	author := strings.TrimSpace(r.URL.Query().Get("author"))

	var rows *sql.Rows
	var err error
	if author != "" {
		rows, err = s.db.Query(
			"SELECT id, title, author, year, isbn FROM books WHERE author LIKE ? ORDER BY id",
			"%"+author+"%",
		)
	} else {
		rows, err = s.db.Query("SELECT id, title, author, year, isbn FROM books ORDER BY id")
	}
	if err != nil {
		respondError(w, http.StatusInternalServerError, "database error")
		return
	}
	defer rows.Close()

	books, err := scanBooks(rows)
	if err != nil {
		respondError(w, http.StatusInternalServerError, "database error")
		return
	}

	respondJSON(w, http.StatusOK, books)
}

func (s *server) getBook(w http.ResponseWriter, r *http.Request) {
	id, err := parseID(r)
	if err != nil {
		respondError(w, http.StatusBadRequest, err.Error())
		return
	}

	book, err := s.bookByID(id)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			respondError(w, http.StatusNotFound, "book not found")
			return
		}
		respondError(w, http.StatusInternalServerError, "database error")
		return
	}

	respondJSON(w, http.StatusOK, book)
}

func (s *server) updateBook(w http.ResponseWriter, r *http.Request) {
	id, err := parseID(r)
	if err != nil {
		respondError(w, http.StatusBadRequest, err.Error())
		return
	}

	var book Book
	if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
		respondError(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	if err := validateBook(&book); err != nil {
		respondError(w, http.StatusBadRequest, err.Error())
		return
	}

	result, err := s.db.Exec(
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
		book.Title, book.Author, book.Year, book.ISBN, id,
	)
	if err != nil {
		respondError(w, http.StatusInternalServerError, "database error")
		return
	}
	rowsAffected, _ := result.RowsAffected()
	if rowsAffected == 0 {
		respondError(w, http.StatusNotFound, "book not found")
		return
	}

	book.ID = id
	respondJSON(w, http.StatusOK, book)
}

func (s *server) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, err := parseID(r)
	if err != nil {
		respondError(w, http.StatusBadRequest, err.Error())
		return
	}

	result, err := s.db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		respondError(w, http.StatusInternalServerError, "database error")
		return
	}
	rowsAffected, _ := result.RowsAffected()
	if rowsAffected == 0 {
		respondError(w, http.StatusNotFound, "book not found")
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

func (s *server) bookByID(id int64) (Book, error) {
	var book Book
	var year sql.NullInt64
	err := s.db.QueryRow(
		"SELECT id, title, author, year, isbn FROM books WHERE id = ?",
		id,
	).Scan(&book.ID, &book.Title, &book.Author, &year, &book.ISBN)
	if err != nil {
		return book, err
	}
	if year.Valid {
		book.Year = int(year.Int64)
	}
	return book, nil
}

func scanBooks(rows *sql.Rows) ([]Book, error) {
	var books []Book
	for rows.Next() {
		var book Book
		var year sql.NullInt64
		if err := rows.Scan(&book.ID, &book.Title, &book.Author, &year, &book.ISBN); err != nil {
			return nil, err
		}
		if year.Valid {
			book.Year = int(year.Int64)
		}
		books = append(books, book)
	}
	return books, rows.Err()
}

func validateBook(book *Book) error {
	book.Title = strings.TrimSpace(book.Title)
	book.Author = strings.TrimSpace(book.Author)
	book.ISBN = strings.TrimSpace(book.ISBN)

	if book.Title == "" {
		return errors.New("title is required")
	}
	if book.Author == "" {
		return errors.New("author is required")
	}
	return nil
}

func parseID(r *http.Request) (int64, error) {
	idStr := r.PathValue("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil || id <= 0 {
		return 0, fmt.Errorf("invalid book id")
	}
	return id, nil
}

func respondJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(payload); err != nil {
		log.Printf("encode response: %v", err)
	}
}

func respondError(w http.ResponseWriter, status int, message string) {
	respondJSON(w, status, map[string]string{"error": message})
}
