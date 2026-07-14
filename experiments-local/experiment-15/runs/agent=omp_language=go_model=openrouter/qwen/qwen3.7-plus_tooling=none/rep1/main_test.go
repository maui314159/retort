package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"

	_ "modernc.org/sqlite"
)

func setupTestApp(t *testing.T) *App {
	db, err := sql.Open("sqlite", ":memory:")
	if err != nil {
		t.Fatalf("Failed to open test database: %v", err)
	}

	app := &App{DB: db}
	if err := app.InitDB(); err != nil {
		t.Fatalf("Failed to initialize test database: %v", err)
	}

	return app
}

func TestCreateBook(t *testing.T) {
	app := setupTestApp(t)

	body := `{"title": "The Go Programming Language", "author": "Alan Donovan", "year": 2015, "isbn": "978-0134190440"}`
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBufferString(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	app.Routes().ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("Expected status %d, got %d", http.StatusCreated, w.Code)
	}

	var book Book
	if err := json.NewDecoder(w.Body).Decode(&book); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if book.Title != "The Go Programming Language" {
		t.Errorf("Expected title 'The Go Programming Language', got '%s'", book.Title)
	}
	if book.ID == 0 {
		t.Errorf("Expected book ID to be set")
	}
}

func TestCreateBookValidation(t *testing.T) {
	app := setupTestApp(t)

	body := `{"title": "", "author": "Alan Donovan"}`
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBufferString(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	app.Routes().ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status %d, got %d", http.StatusBadRequest, w.Code)
	}
}

func TestGetBooks(t *testing.T) {
	app := setupTestApp(t)

	app.DB.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", "Test Book", "Test Author", 2020, "123456")
	app.DB.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", "Another Book", "Another Author", 2021, "654321")

	req := httptest.NewRequest(http.MethodGet, "/books", nil)
	w := httptest.NewRecorder()

	app.Routes().ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
	}

	var books []Book
	if err := json.NewDecoder(w.Body).Decode(&books); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if len(books) != 2 {
		t.Errorf("Expected 2 books, got %d", len(books))
	}
}

func TestGetBooksWithAuthorFilter(t *testing.T) {
	app := setupTestApp(t)

	app.DB.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", "Test Book", "Test Author", 2020, "123456")
	app.DB.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", "Another Book", "Another Author", 2021, "654321")

	req := httptest.NewRequest(http.MethodGet, "/books?author=Test", nil)
	w := httptest.NewRecorder()

	app.Routes().ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
	}

	var books []Book
	if err := json.NewDecoder(w.Body).Decode(&books); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if len(books) != 1 {
		t.Errorf("Expected 1 book, got %d", len(books))
	}
	if books[0].Author != "Test Author" {
		t.Errorf("Expected author 'Test Author', got '%s'", books[0].Author)
	}
}

func TestGetBookNotFound(t *testing.T) {
	app := setupTestApp(t)

	req := httptest.NewRequest(http.MethodGet, "/books/999", nil)
	w := httptest.NewRecorder()

	app.Routes().ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status %d, got %d", http.StatusNotFound, w.Code)
	}
}

func TestUpdateBook(t *testing.T) {
	app := setupTestApp(t)

	res, err := app.DB.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", "Old Title", "Old Author", 2000, "000000")
	if err != nil {
		t.Fatalf("Failed to seed database: %v", err)
	}
	id, _ := res.LastInsertId()

	body := `{"title": "New Title", "author": "New Author", "year": 2023, "isbn": "111111"}`
	req := httptest.NewRequest(http.MethodPut, "/books/"+strconv.FormatInt(id, 10), bytes.NewBufferString(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	app.Routes().ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
	}

	var book Book
	if err := json.NewDecoder(w.Body).Decode(&book); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if book.Title != "New Title" {
		t.Errorf("Expected title 'New Title', got '%s'", book.Title)
	}
}

func TestDeleteBook(t *testing.T) {
	app := setupTestApp(t)

	res, err := app.DB.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", "To Delete", "Author", 2020, "999999")
	if err != nil {
		t.Fatalf("Failed to seed database: %v", err)
	}
	id, _ := res.LastInsertId()

	req := httptest.NewRequest(http.MethodDelete, "/books/"+strconv.FormatInt(id, 10), nil)
	w := httptest.NewRecorder()

	app.Routes().ServeHTTP(w, req)

	if w.Code != http.StatusNoContent {
		t.Errorf("Expected status %d, got %d", http.StatusNoContent, w.Code)
	}

	var count int
	app.DB.QueryRow("SELECT COUNT(*) FROM books WHERE id = ?", id).Scan(&count)
	if count != 0 {
		t.Errorf("Expected book to be deleted, but it still exists")
	}
}
