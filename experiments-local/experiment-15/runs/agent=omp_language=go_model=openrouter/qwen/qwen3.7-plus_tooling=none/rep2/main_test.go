package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strconv"
	"testing"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func setupTestServer(t *testing.T) *httptest.Server {
	store, err := NewStore(":memory:")
	require.NoError(t, err)

	server := NewServer(store)

	r := chi.NewRouter()
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)

	r.Get("/health", server.HealthCheck)
	r.Post("/books", server.CreateBook)
	r.Get("/books", server.ListBooks)
	r.Get("/books/{id}", server.GetBook)
	r.Put("/books/{id}", server.UpdateBook)
	r.Delete("/books/{id}", server.DeleteBook)

	return httptest.NewServer(r)
}

func TestHealthCheck(t *testing.T) {
	ts := setupTestServer(t)
	defer ts.Close()

	resp, err := http.Get(ts.URL + "/health")
	require.NoError(t, err)
	defer resp.Body.Close()

	assert.Equal(t, http.StatusOK, resp.StatusCode)

	var result map[string]string
	err = json.NewDecoder(resp.Body).Decode(&result)
	require.NoError(t, err)
	assert.Equal(t, "healthy", result["status"])
}

func TestCreateAndGetBook(t *testing.T) {
	ts := setupTestServer(t)
	defer ts.Close()

	book := Book{
		Title:  "The Go Programming Language",
		Author: "Alan A. A. Donovan",
		Year:   2015,
		ISBN:   "978-0134190440",
	}

	body, _ := json.Marshal(book)
	resp, err := http.Post(ts.URL+"/books", "application/json", bytes.NewBuffer(body))
	require.NoError(t, err)
	defer resp.Body.Close()

	assert.Equal(t, http.StatusCreated, resp.StatusCode)

	var createdBook Book
	err = json.NewDecoder(resp.Body).Decode(&createdBook)
	require.NoError(t, err)
	assert.NotZero(t, createdBook.ID)
	assert.Equal(t, book.Title, createdBook.Title)
	assert.Equal(t, book.Author, createdBook.Author)

	getResp, err := http.Get(ts.URL + "/books/" + fmt.Sprintf("%d", createdBook.ID))
	require.NoError(t, err)
	defer getResp.Body.Close()

	assert.Equal(t, http.StatusOK, getResp.StatusCode)

	var fetchedBook Book
	err = json.NewDecoder(getResp.Body).Decode(&fetchedBook)
	require.NoError(t, err)
	assert.Equal(t, createdBook.ID, fetchedBook.ID)
}

func TestCreateBookValidation(t *testing.T) {
	ts := setupTestServer(t)
	defer ts.Close()

	// Missing Title
	book := Book{
		Author: "Test Author",
	}
	body, _ := json.Marshal(book)
	resp, err := http.Post(ts.URL+"/books", "application/json", bytes.NewBuffer(body))
	require.NoError(t, err)
	defer resp.Body.Close()

	assert.Equal(t, http.StatusBadRequest, resp.StatusCode)

	// Missing Author
	book2 := Book{
		Title: "Test Title",
	}
	body2, _ := json.Marshal(book2)
	resp2, err := http.Post(ts.URL+"/books", "application/json", bytes.NewBuffer(body2))
	require.NoError(t, err)
	defer resp2.Body.Close()

	assert.Equal(t, http.StatusBadRequest, resp2.StatusCode)
}

func TestListBooksWithFilter(t *testing.T) {
	ts := setupTestServer(t)
	defer ts.Close()

	books := []Book{
		{Title: "Book 1", Author: "Author A", Year: 2020, ISBN: "111"},
		{Title: "Book 2", Author: "Author B", Year: 2021, ISBN: "222"},
		{Title: "Book 3", Author: "Author A", Year: 2022, ISBN: "333"},
	}

	for _, b := range books {
		body, _ := json.Marshal(b)
		resp, err := http.Post(ts.URL+"/books", "application/json", bytes.NewBuffer(body))
		if err != nil {
			t.Fatalf("Failed to create book: %v", err)
		}
		if resp.StatusCode != http.StatusCreated {
			bodyBytes, _ := io.ReadAll(resp.Body)
			t.Fatalf("Failed to create book, status: %d, body: %s", resp.StatusCode, string(bodyBytes))
		}
		resp.Body.Close()
	}

	filteredURL := ts.URL + "/books?author=" + url.QueryEscape("Author A")
	resp, err := http.Get(filteredURL)
	require.NoError(t, err)
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		bodyBytes, _ := io.ReadAll(resp.Body)
		t.Fatalf("Failed to list books, status: %d, body: %s", resp.StatusCode, string(bodyBytes))
	}

	var fetchedBooks []Book
	err = json.NewDecoder(resp.Body).Decode(&fetchedBooks)
	require.NoError(t, err)
	assert.Len(t, fetchedBooks, 2)
	for _, b := range fetchedBooks {
		assert.Contains(t, b.Author, "Author A")
	}
}

func TestUpdateAndDeleteBook(t *testing.T) {
	ts := setupTestServer(t)
	defer ts.Close()

	// Create book
	book := Book{Title: "Old Title", Author: "Old Author", Year: 1990, ISBN: "000"}
	body, _ := json.Marshal(book)
	resp, _ := http.Post(ts.URL+"/books", "application/json", bytes.NewBuffer(body))
	var createdBook Book
	json.NewDecoder(resp.Body).Decode(&createdBook)

	// Update book
	updatedBook := Book{Title: "New Title", Author: "New Author", Year: 2000, ISBN: "001"}
	updateBody, _ := json.Marshal(updatedBook)
	req, _ := http.NewRequest(http.MethodPut, ts.URL+"/books/"+strconv.Itoa(createdBook.ID), bytes.NewBuffer(updateBody))
	req.Header.Set("Content-Type", "application/json")
	client := &http.Client{}
	putResp, err := client.Do(req)
	require.NoError(t, err)
	defer putResp.Body.Close()

	assert.Equal(t, http.StatusOK, putResp.StatusCode)

	var respUpdatedBook Book
	err = json.NewDecoder(putResp.Body).Decode(&respUpdatedBook)
	require.NoError(t, err)
	assert.Equal(t, "New Title", respUpdatedBook.Title)
	assert.Equal(t, "New Author", respUpdatedBook.Author)

	// Delete book
	delReq, _ := http.NewRequest(http.MethodDelete, ts.URL+"/books/"+strconv.Itoa(createdBook.ID), nil)
	delResp, err := client.Do(delReq)
	require.NoError(t, err)
	defer delResp.Body.Close()
	assert.Equal(t, http.StatusNoContent, delResp.StatusCode)

	// Verify deletion
	getResp, err := http.Get(ts.URL + "/books/" + strconv.Itoa(createdBook.ID))
	require.NoError(t, err)
	defer getResp.Body.Close()
	assert.Equal(t, http.StatusNotFound, getResp.StatusCode)
}
