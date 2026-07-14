package main

import (
	"database/sql"
	"encoding/json"
	"log"
	"net/http"
	"strconv"
	"time"

	"github.com/gorilla/mux"
	_ "modernc.org/sqlite"
)

type Book struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year,omitempty"`
	ISBN   string `json:"isbn,omitempty"`
}

type BookStore struct {
	db *sql.DB
}

func NewBookStore(dbPath string) (*BookStore, error) {
	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		return nil, err
	}

	createTable := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT
	);`

	_, err = db.Exec(createTable)
	if err != nil {
		return nil, err
	}

	return &BookStore{db: db}, nil
}

func (bs *BookStore) CreateBook(book *Book) error {
	result, err := bs.db.Exec(
		"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		book.Title, book.Author, book.Year, book.ISBN,
	)
	if err != nil {
		return err
	}

	id, err := result.LastInsertId()
	if err != nil {
		return err
	}

	book.ID = int(id)
	return nil
}

func (bs *BookStore) GetAllBooks(authorFilter string) ([]Book, error) {
	query := "SELECT id, title, author, year, isbn FROM books"
	args := []interface{}{}

	if authorFilter != "" {
		query += " WHERE author LIKE ?"
		args = append(args, "%"+authorFilter+"%")
	}

	rows, err := bs.db.Query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	books := []Book{}
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return nil, err
		}
		books = append(books, b)
	}

	return books, nil
}

func (bs *BookStore) GetBookByID(id int) (*Book, error) {
	var b Book
	err := bs.db.QueryRow(
		"SELECT id, title, author, year, isbn FROM books WHERE id = ?", id,
	).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)

	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}

	return &b, nil
}

func (bs *BookStore) UpdateBook(book *Book) error {
	result, err := bs.db.Exec(
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
		book.Title, book.Author, book.Year, book.ISBN, book.ID,
	)
	if err != nil {
		return err
	}

	rows, err := result.RowsAffected()
	if err != nil {
		return err
	}

	if rows == 0 {
		return sql.ErrNoRows
	}

	return nil
}

func (bs *BookStore) DeleteBook(id int) error {
	result, err := bs.db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		return err
	}

	rows, err := result.RowsAffected()
	if err != nil {
		return err
	}

	if rows == 0 {
		return sql.ErrNoRows
	}

	return nil
}

func (bs *BookStore) Close() error {
	return bs.db.Close()
}

type App struct {
	store *BookStore
}

func NewApp(store *BookStore) *App {
	return &App{store: store}
}

func (a *App) CreateBook(w http.ResponseWriter, r *http.Request) {
	var book Book
	if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
		http.Error(w, `{"error":"Invalid JSON"}`, http.StatusBadRequest)
		return
	}

	if book.Title == "" || book.Author == "" {
		http.Error(w, `{"error":"Title and author are required"}`, http.StatusBadRequest)
		return
	}

	if err := a.store.CreateBook(&book); err != nil {
		http.Error(w, `{"error":"Failed to create book"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(book)
}

func (a *App) GetBooks(w http.ResponseWriter, r *http.Request) {
	authorFilter := r.URL.Query().Get("author")

	books, err := a.store.GetAllBooks(authorFilter)
	if err != nil {
		http.Error(w, `{"error":"Failed to fetch books"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(books)
}

func (a *App) GetBook(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id, err := strconv.Atoi(vars["id"])
	if err != nil {
		http.Error(w, `{"error":"Invalid book ID"}`, http.StatusBadRequest)
		return
	}

	book, err := a.store.GetBookByID(id)
	if err != nil {
		http.Error(w, `{"error":"Failed to fetch book"}`, http.StatusInternalServerError)
		return
	}

	if book == nil {
		http.Error(w, `{"error":"Book not found"}`, http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(book)
}

func (a *App) UpdateBook(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id, err := strconv.Atoi(vars["id"])
	if err != nil {
		http.Error(w, `{"error":"Invalid book ID"}`, http.StatusBadRequest)
		return
	}

	var book Book
	if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
		http.Error(w, `{"error":"Invalid JSON"}`, http.StatusBadRequest)
		return
	}

	if book.Title == "" || book.Author == "" {
		http.Error(w, `{"error":"Title and author are required"}`, http.StatusBadRequest)
		return
	}

	book.ID = id
	if err := a.store.UpdateBook(&book); err != nil {
		if err == sql.ErrNoRows {
			http.Error(w, `{"error":"Book not found"}`, http.StatusNotFound)
			return
		}
		http.Error(w, `{"error":"Failed to update book"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(book)
}

func (a *App) DeleteBook(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id, err := strconv.Atoi(vars["id"])
	if err != nil {
		http.Error(w, `{"error":"Invalid book ID"}`, http.StatusBadRequest)
		return
	}

	if err := a.store.DeleteBook(id); err != nil {
		if err == sql.ErrNoRows {
			http.Error(w, `{"error":"Book not found"}`, http.StatusNotFound)
			return
		}
		http.Error(w, `{"error":"Failed to delete book"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusNoContent)
}

func (a *App) HealthCheck(w http.ResponseWriter, r *http.Request) {
	if err := a.store.db.Ping(); err != nil {
		http.Error(w, `{"status":"unhealthy"}`, http.StatusServiceUnavailable)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
}

func main() {
	store, err := NewBookStore("./books.db")
	if err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
	defer store.Close()

	app := NewApp(store)

	r := mux.NewRouter()
	r.HandleFunc("/books", app.CreateBook).Methods("POST")
	r.HandleFunc("/books", app.GetBooks).Methods("GET")
	r.HandleFunc("/books/{id}", app.GetBook).Methods("GET")
	r.HandleFunc("/books/{id}", app.UpdateBook).Methods("PUT")
	r.HandleFunc("/books/{id}", app.DeleteBook).Methods("DELETE")
	r.HandleFunc("/health", app.HealthCheck).Methods("GET")

	srv := &http.Server{
		Handler:      r,
		Addr:         ":8080",
		WriteTimeout: 15 * time.Second,
		ReadTimeout:  15 * time.Second,
	}

	log.Println("Server starting on :8080")
	log.Fatal(srv.ListenAndServe())
}
