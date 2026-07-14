package main

import (
	"testing"
	
	"bookapi/internal/models"
)

// Example test to demonstrate the book model structure
func TestExampleBookCreation(t *testing.T) {
	book := models.Book{
		Title:  "Example Book",
		Author: "Example Author",
		Year:   2024,
		ISBN:   "978-3-16-148410-0",
	}
	
	if book.Title != "Example Book" {
		t.Errorf("Expected title 'Example Book', got %s", book.Title)
	}
	
	if book.Author != "Example Author" {
		t.Errorf("Expected author 'Example Author', got %s", book.Author)
	}
	
	if book.Year != 2024 {
		t.Errorf("Expected year 2024, got %d", book.Year)
	}
	
	if book.ISBN != "978-3-16-148410-0" {
		t.Errorf("Expected ISBN '978-3-16-148410-0', got %s", book.ISBN)
	}
}