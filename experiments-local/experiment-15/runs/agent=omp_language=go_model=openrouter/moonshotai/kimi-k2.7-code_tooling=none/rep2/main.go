package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"

	_ "github.com/mattn/go-sqlite3"
)

const defaultDBFile = "books.db"

type Book struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type bookRequest struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type errorResponse struct {
	Error string `json:"error"`
}

type Server struct {
	db *sql.DB
}

func main() {
	dbFile := os.Getenv("DB_FILE")
	if dbFile == "" {
		dbFile = defaultDBFile
	}

	db, err := openDB(dbFile)
	if err != nil {
		log.Fatalf("failed to open database: %v", err)
	}
	defer db.Close()

	srv := &Server{db: db}
	router := srv.routes()

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	log.Printf("Server listening on :%s", port)
	if err := http.ListenAndServe(":"+port, router); err != nil {
		log.Fatalf("server error: %v", err)
	}
}

func openDB(dbFile string) (*sql.DB, error) {
	db, err := sql.Open("sqlite3", dbFile)
	if err != nil {
		return nil, err
	}
	if err := db.Ping(); err != nil {
		return nil, err
	}
	createSQL := `CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT
	);`
	if _, err := db.Exec(createSQL); err != nil {
		return nil, err
	}
	return db, nil
}

func (s *Server) routes() *http.ServeMux {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", s.healthHandler)
	mux.HandleFunc("POST /books", s.createBookHandler)
	mux.HandleFunc("GET /books", s.listBooksHandler)
	mux.HandleFunc("GET /books/{id}", s.getBookHandler)
	mux.HandleFunc("PUT /books/{id}", s.updateBookHandler)
	mux.HandleFunc("DELETE /books/{id}", s.deleteBookHandler)
	return mux
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, errorResponse{Error: message})
}

func (s *Server) healthHandler(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) createBookHandler(w http.ResponseWriter, r *http.Request) {
	var req bookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON")
		return
	}

	if strings.TrimSpace(req.Title) == "" || strings.TrimSpace(req.Author) == "" {
		writeError(w, http.StatusBadRequest, "title and author are required")
		return
	}

	result, err := s.db.Exec(
		"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		req.Title, req.Author, req.Year, req.ISBN,
	)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to create book")
		return
	}

	id, err := result.LastInsertId()
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to retrieve book id")
		return
	}

	book := Book{
		ID:     int(id),
		Title:  req.Title,
		Author: req.Author,
		Year:   req.Year,
		ISBN:   req.ISBN,
	}
	writeJSON(w, http.StatusCreated, book)
}

func (s *Server) listBooksHandler(w http.ResponseWriter, r *http.Request) {
	authorFilter := r.URL.Query().Get("author")

	var rows *sql.Rows
	var err error
	if authorFilter != "" {
		rows, err = s.db.Query("SELECT id, title, author, year, isbn FROM books WHERE author = ?", authorFilter)
	} else {
		rows, err = s.db.Query("SELECT id, title, author, year, isbn FROM books")
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to list books")
		return
	}
	defer rows.Close()

	books := []Book{}
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			writeError(w, http.StatusInternalServerError, "failed to read book")
			return
		}
		books = append(books, b)
	}

	writeJSON(w, http.StatusOK, books)
}

func (s *Server) getBookHandler(w http.ResponseWriter, r *http.Request) {
	id, err := strconv.Atoi(r.PathValue("id"))
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return
	}

	var b Book
	err = s.db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).
		Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "book not found")
			return
		}
		writeError(w, http.StatusInternalServerError, "failed to get book")
		return
	}

	writeJSON(w, http.StatusOK, b)
}

func (s *Server) updateBookHandler(w http.ResponseWriter, r *http.Request) {
	id, err := strconv.Atoi(r.PathValue("id"))
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return
	}

	var req bookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON")
		return
	}

	if strings.TrimSpace(req.Title) == "" || strings.TrimSpace(req.Author) == "" {
		writeError(w, http.StatusBadRequest, "title and author are required")
		return
	}

	result, err := s.db.Exec(
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
		req.Title, req.Author, req.Year, req.ISBN, id,
	)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to update book")
		return
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to verify update")
		return
	}
	if rowsAffected == 0 {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}

	book := Book{
		ID:     id,
		Title:  req.Title,
		Author: req.Author,
		Year:   req.Year,
		ISBN:   req.ISBN,
	}
	writeJSON(w, http.StatusOK, book)
}

func (s *Server) deleteBookHandler(w http.ResponseWriter, r *http.Request) {
	id, err := strconv.Atoi(r.PathValue("id"))
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return
	}

	result, err := s.db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to delete book")
		return
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to verify deletion")
		return
	}
	if rowsAffected == 0 {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}

	w.WriteHeader(http.StatusNoContent)
}
