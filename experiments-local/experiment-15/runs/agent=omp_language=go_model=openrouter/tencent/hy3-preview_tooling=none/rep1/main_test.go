package main

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gorilla/mux"
	_ "modernc.org/sqlite"
)

func setupTestDB(t *testing.T) *BookStore {
	t.Helper()
	store, err := NewBookStore(":memory:")
	if err != nil {
		t.Fatalf("Failed to create test database: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return store
}

func setupTestApp(store *BookStore) *App {
	return NewApp(store)
}

func TestCreateBook(t *testing.T) {
	store := setupTestDB(t)
	app := setupTestApp(store)

	tests := []struct {
		name       string
		body       string
		wantStatus int
		wantError  bool
	}{
		{
			name:       "valid book",
			body:       `{"title":"1984","author":"George Orwell","year":1949,"isbn":"9780451524935"}`,
			wantStatus: http.StatusCreated,
			wantError:  false,
		},
		{
			name:       "missing title",
			body:       `{"author":"George Orwell"}`,
			wantStatus: http.StatusBadRequest,
			wantError:  true,
		},
		{
			name:       "missing author",
			body:       `{"title":"1984"}`,
			wantStatus: http.StatusBadRequest,
			wantError:  true,
		},
		{
			name:       "invalid JSON",
			body:       `{"title":"1984",}`,
			wantStatus: http.StatusBadRequest,
			wantError:  true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			req := httptest.NewRequest(http.MethodPost, "/books", strings.NewReader(tt.body))
			req.Header.Set("Content-Type", "application/json")
			rr := httptest.NewRecorder()

			app.CreateBook(rr, req)

			if rr.Code != tt.wantStatus {
				t.Errorf("expected status %d, got %d", tt.wantStatus, rr.Code)
			}

			if !tt.wantError {
				var book Book
				if err := json.NewDecoder(rr.Body).Decode(&book); err != nil {
					t.Errorf("failed to decode response: %v", err)
				}
				if book.ID == 0 {
					t.Error("expected book to have an ID")
				}
				if book.Title == "" {
					t.Error("expected book to have a title")
				}
			}
		})
	}
}

func TestGetBooks(t *testing.T) {
	store := setupTestDB(t)
	app := setupTestApp(store)

	books := []Book{
		{Title: "1984", Author: "George Orwell", Year: 1949, ISBN: "9780451524935"},
		{Title: "Animal Farm", Author: "George Orwell", Year: 1945, ISBN: "9780451526342"},
		{Title: "Brave New World", Author: "Aldous Huxley", Year: 1932, ISBN: "9780060850524"},
	}

	for _, b := range books {
		if err := store.CreateBook(&b); err != nil {
			t.Fatalf("Failed to create test book: %v", err)
		}
	}

	t.Run("get all books", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodGet, "/books", nil)
		rr := httptest.NewRecorder()

		app.GetBooks(rr, req)

		if rr.Code != http.StatusOK {
			t.Errorf("expected status 200, got %d", rr.Code)
		}

		var result []Book
		if err := json.NewDecoder(rr.Body).Decode(&result); err != nil {
			t.Errorf("failed to decode response: %v", err)
		}

		if len(result) != 3 {
			t.Errorf("expected 3 books, got %d", len(result))
		}
	})

	t.Run("filter by author", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodGet, "/books?author=Orwell", nil)
		rr := httptest.NewRecorder()

		app.GetBooks(rr, req)

		if rr.Code != http.StatusOK {
			t.Errorf("expected status 200, got %d", rr.Code)
		}

		var result []Book
		if err := json.NewDecoder(rr.Body).Decode(&result); err != nil {
			t.Errorf("failed to decode response: %v", err)
		}

		if len(result) != 2 {
			t.Errorf("expected 2 books by Orwell, got %d", len(result))
		}

		for _, b := range result {
			if !strings.Contains(b.Author, "Orwell") {
				t.Errorf("expected author to contain 'Orwell', got %s", b.Author)
			}
		}
	})
}

func TestGetBookByID(t *testing.T) {
	store := setupTestDB(t)
	app := setupTestApp(store)

	book := Book{Title: "1984", Author: "George Orwell", Year: 1949, ISBN: "9780451524935"}
	if err := store.CreateBook(&book); err != nil {
		t.Fatalf("Failed to create test book: %v", err)
	}

	t.Run("existing book", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodGet, "/books/1", nil)
		rr := httptest.NewRecorder()

		router := mux.NewRouter()
		router.HandleFunc("/books/{id}", app.GetBook).Methods("GET")
		router.ServeHTTP(rr, req)

		if rr.Code != http.StatusOK {
			t.Errorf("expected status 200, got %d", rr.Code)
		}

		var result Book
		if err := json.NewDecoder(rr.Body).Decode(&result); err != nil {
			t.Errorf("failed to decode response: %v", err)
		}

		if result.ID != 1 {
			t.Errorf("expected ID 1, got %d", result.ID)
		}
		if result.Title != "1984" {
			t.Errorf("expected title '1984', got %s", result.Title)
		}
	})

	t.Run("non-existent book", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodGet, "/books/999", nil)
		rr := httptest.NewRecorder()

		router := mux.NewRouter()
		router.HandleFunc("/books/{id}", app.GetBook).Methods("GET")
		router.ServeHTTP(rr, req)

		if rr.Code != http.StatusNotFound {
			t.Errorf("expected status 404, got %d", rr.Code)
		}
	})

	t.Run("invalid ID", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodGet, "/books/abc", nil)
		rr := httptest.NewRecorder()

		router := mux.NewRouter()
		router.HandleFunc("/books/{id}", app.GetBook).Methods("GET")
		router.ServeHTTP(rr, req)

		if rr.Code != http.StatusBadRequest {
			t.Errorf("expected status 400, got %d", rr.Code)
		}
	})
}

func TestUpdateBook(t *testing.T) {
	store := setupTestDB(t)
	app := setupTestApp(store)

	book := Book{Title: "1984", Author: "George Orwell", Year: 1949, ISBN: "9780451524935"}
	if err := store.CreateBook(&book); err != nil {
		t.Fatalf("Failed to create test book: %v", err)
	}

	t.Run("valid update", func(t *testing.T) {
		body := `{"title":"1984 (Updated)","author":"George Orwell","year":1950,"isbn":"9780451524936"}`
		req := httptest.NewRequest(http.MethodPut, "/books/1", strings.NewReader(body))
		req.Header.Set("Content-Type", "application/json")
		rr := httptest.NewRecorder()

		router := mux.NewRouter()
		router.HandleFunc("/books/{id}", app.UpdateBook).Methods("PUT")
		router.ServeHTTP(rr, req)

		if rr.Code != http.StatusOK {
			t.Errorf("expected status 200, got %d", rr.Code)
		}

		var result Book
		if err := json.NewDecoder(rr.Body).Decode(&result); err != nil {
			t.Errorf("failed to decode response: %v", err)
		}

		if result.Title != "1984 (Updated)" {
			t.Errorf("expected updated title, got %s", result.Title)
		}
		if result.Year != 1950 {
			t.Errorf("expected updated year, got %d", result.Year)
		}
	})

	t.Run("non-existent book", func(t *testing.T) {
		body := `{"title":"Test","author":"Author","year":2023,"isbn":"123"}`
		req := httptest.NewRequest(http.MethodPut, "/books/999", strings.NewReader(body))
		req.Header.Set("Content-Type", "application/json")
		rr := httptest.NewRecorder()

		router := mux.NewRouter()
		router.HandleFunc("/books/{id}", app.UpdateBook).Methods("PUT")
		router.ServeHTTP(rr, req)

		if rr.Code != http.StatusNotFound {
			t.Errorf("expected status 404, got %d", rr.Code)
		}
	})

	t.Run("missing required fields", func(t *testing.T) {
		body := `{"title":"Only Title"}`
		req := httptest.NewRequest(http.MethodPut, "/books/1", strings.NewReader(body))
		req.Header.Set("Content-Type", "application/json")
		rr := httptest.NewRecorder()

		router := mux.NewRouter()
		router.HandleFunc("/books/{id}", app.UpdateBook).Methods("PUT")
		router.ServeHTTP(rr, req)

		if rr.Code != http.StatusBadRequest {
			t.Errorf("expected status 400, got %d", rr.Code)
		}
	})
}

func TestDeleteBook(t *testing.T) {
	store := setupTestDB(t)
	app := setupTestApp(store)

	book := Book{Title: "1984", Author: "George Orwell", Year: 1949, ISBN: "9780451524935"}
	if err := store.CreateBook(&book); err != nil {
		t.Fatalf("Failed to create test book: %v", err)
	}

	t.Run("delete existing book", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodDelete, "/books/1", nil)
		rr := httptest.NewRecorder()

		router := mux.NewRouter()
		router.HandleFunc("/books/{id}", app.DeleteBook).Methods("DELETE")
		router.ServeHTTP(rr, req)

		if rr.Code != http.StatusNoContent {
			t.Errorf("expected status 204, got %d", rr.Code)
		}

		retrieved, err := store.GetBookByID(1)
		if err != nil {
			t.Fatalf("Failed to check deleted book: %v", err)
		}
		if retrieved != nil {
			t.Error("expected book to be deleted")
		}
	})

	t.Run("delete non-existent book", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodDelete, "/books/999", nil)
		rr := httptest.NewRecorder()

		router := mux.NewRouter()
		router.HandleFunc("/books/{id}", app.DeleteBook).Methods("DELETE")
		router.ServeHTTP(rr, req)

		if rr.Code != http.StatusNotFound {
			t.Errorf("expected status 404, got %d", rr.Code)
		}
	})
}

func TestHealthCheck(t *testing.T) {
	store := setupTestDB(t)
	app := setupTestApp(store)

	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	rr := httptest.NewRecorder()

	app.HealthCheck(rr, req)

	if rr.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", rr.Code)
	}

	body, _ := io.ReadAll(rr.Body)
	if !bytes.Contains(body, []byte(`"status":"healthy"`)) {
		t.Errorf("expected healthy status, got %s", string(body))
	}
}

func TestBookStoreOperations(t *testing.T) {
	store := setupTestDB(t)

	t.Run("create and retrieve book", func(t *testing.T) {
		book := &Book{Title: "Test Book", Author: "Test Author", Year: 2023, ISBN: "1234567890"}
		if err := store.CreateBook(book); err != nil {
			t.Fatalf("Failed to create book: %v", err)
		}

		retrieved, err := store.GetBookByID(book.ID)
		if err != nil {
			t.Fatalf("Failed to get book: %v", err)
		}

		if retrieved == nil {
			t.Fatal("Expected book to be retrieved")
		}

		if retrieved.Title != "Test Book" {
			t.Errorf("expected title 'Test Book', got %s", retrieved.Title)
		}
	})

	t.Run("update book", func(t *testing.T) {
		book := &Book{Title: "Original", Author: "Author", Year: 2020, ISBN: "111"}
		if err := store.CreateBook(book); err != nil {
			t.Fatalf("Failed to create book: %v", err)
		}

		book.Title = "Updated"
		book.Year = 2021
		if err := store.UpdateBook(book); err != nil {
			t.Fatalf("Failed to update book: %v", err)
		}

		retrieved, _ := store.GetBookByID(book.ID)
		if retrieved.Title != "Updated" {
			t.Errorf("expected updated title, got %s", retrieved.Title)
		}
		if retrieved.Year != 2021 {
			t.Errorf("expected updated year, got %d", retrieved.Year)
		}
	})

	t.Run("delete book", func(t *testing.T) {
		book := &Book{Title: "To Delete", Author: "Author", Year: 2020, ISBN: "222"}
		if err := store.CreateBook(book); err != nil {
			t.Fatalf("Failed to create book: %v", err)
		}

		if err := store.DeleteBook(book.ID); err != nil {
			t.Fatalf("Failed to delete book: %v", err)
		}

		retrieved, _ := store.GetBookByID(book.ID)
		if retrieved != nil {
			t.Error("Expected book to be deleted")
		}
	})
}
