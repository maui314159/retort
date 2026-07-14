package db

import (
	"testing"

	"bookapi/internal/models"

	"github.com/stretchr/testify/assert"
)

func TestCreateAndGetBook(t *testing.T) {
	db := setupTestDB(t)
	DB = db // Use test database

	// Create book
	book := &models.Book{
		Title:  "Test Book",
		Author: "Test Author",
		Year:   2023,
		ISBN:   "1234567890",
	}

	err := CreateBook(book)
	assert.NoError(t, err)
	assert.NotZero(t, book.ID)

	// Get book
	retrieved, err := GetBookByID(book.ID)
	assert.NoError(t, err)
	assert.NotNil(t, retrieved)
	assert.Equal(t, book.Title, retrieved.Title)
	assert.Equal(t, book.Author, retrieved.Author)
	assert.Equal(t, book.Year, retrieved.Year)
	assert.Equal(t, book.ISBN, retrieved.ISBN)
}

func TestGetAllBooks(t *testing.T) {
	db := setupTestDB(t)
	DB = db

	// Create test books
	books := []*models.Book{
		{Title: "Book 1", Author: "Author A", Year: 2020, ISBN: "111"},
		{Title: "Book 2", Author: "Author B", Year: 2021, ISBN: "222"},
		{Title: "Book 3", Author: "Author A", Year: 2022, ISBN: "333"},
	}

	for _, book := range books {
		err := CreateBook(book)
		assert.NoError(t, err)
	}

	// Get all books
	allBooks, err := GetAllBooks("")
	assert.NoError(t, err)
	assert.Len(t, allBooks, 3)

	// Filter by author
	filteredBooks, err := GetAllBooks("Author A")
	assert.NoError(t, err)
	assert.Len(t, filteredBooks, 2)
}

func TestUpdateBook(t *testing.T) {
	db := setupTestDB(t)
	DB = db

	// Create book
	book := &models.Book{
		Title:  "Original Title",
		Author: "Original Author",
		Year:   2020,
		ISBN:   "original",
	}
	err := CreateBook(book)
	assert.NoError(t, err)

	// Update book
	updatedBook := &models.Book{
		Title:  "Updated Title",
		Author: "Updated Author",
		Year:   2024,
		ISBN:   "updated",
	}
	err = UpdateBook(book.ID, updatedBook)
	assert.NoError(t, err)

	// Verify update
	retrieved, err := GetBookByID(book.ID)
	assert.NoError(t, err)
	assert.Equal(t, "Updated Title", retrieved.Title)
	assert.Equal(t, "Updated Author", retrieved.Author)
	assert.Equal(t, 2024, retrieved.Year)
	assert.Equal(t, "updated", retrieved.ISBN)
}

func TestDeleteBook(t *testing.T) {
	db := setupTestDB(t)
	DB = db

	// Create book
	book := &models.Book{
		Title:  "To Delete",
		Author: "Author",
		Year:   2023,
		ISBN:   "delete",
	}
	err := CreateBook(book)
	assert.NoError(t, err)

	// Delete book
	err = DeleteBook(book.ID)
	assert.NoError(t, err)

	// Verify deletion
	deleted, err := GetBookByID(book.ID)
	assert.NoError(t, err)
	assert.Nil(t, deleted)
}

func TestGetNonExistentBook(t *testing.T) {
	db := setupTestDB(t)
	DB = db

	book, err := GetBookByID(999)
	assert.NoError(t, err)
	assert.Nil(t, book)
}