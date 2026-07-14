package store

import (
	"errors"
	"testing"

	"bookapi/internal/models"
)

func newTestStore(t *testing.T) *Store {
	t.Helper()
	s, err := Open(":memory:")
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	t.Cleanup(func() { _ = s.Close() })
	return s
}

func bookInput(title, author string, year int, isbn string) models.BookInput {
	return models.BookInput{Title: title, Author: author, Year: year, ISBN: isbn}
}

func TestStoreCreateAndGet(t *testing.T) {
	s := newTestStore(t)

	b, err := s.Create(bookInput("The Hobbit", "J.R.R. Tolkien", 1937, "978-0261102217"))
	if err != nil {
		t.Fatalf("create: %v", err)
	}
	if b.ID == 0 {
		t.Fatal("expected non-zero id")
	}

	got, err := s.Get(b.ID)
	if err != nil {
		t.Fatalf("get: %v", err)
	}
	if got.Title != "The Hobbit" || got.Author != "J.R.R. Tolkien" || got.Year != 1937 {
		t.Fatalf("unexpected book: %+v", got)
	}
}

func TestStoreGetNotFound(t *testing.T) {
	s := newTestStore(t)
	_, err := s.Get(999)
	if !errors.Is(err, ErrNotFound) {
		t.Fatalf("expected ErrNotFound, got %v", err)
	}
}

func TestStoreListAndFilter(t *testing.T) {
	s := newTestStore(t)
	if _, err := s.Create(bookInput("Book A", "Alice", 2001, "")); err != nil {
		t.Fatal(err)
	}
	if _, err := s.Create(bookInput("Book B", "Bob", 2002, "")); err != nil {
		t.Fatal(err)
	}
	if _, err := s.Create(bookInput("Book C", "Alice", 2003, "")); err != nil {
		t.Fatal(err)
	}

	all, err := s.List("")
	if err != nil {
		t.Fatalf("list all: %v", err)
	}
	if len(all) != 3 {
		t.Fatalf("expected 3 books, got %d", len(all))
	}

	alice, err := s.List("Alice")
	if err != nil {
		t.Fatalf("list alice: %v", err)
	}
	if len(alice) != 2 {
		t.Fatalf("expected 2 alice books, got %d", len(alice))
	}
}

func TestStoreUpdateAndDelete(t *testing.T) {
	s := newTestStore(t)
	b, err := s.Create(bookInput("Old", "Author", 1900, ""))
	if err != nil {
		t.Fatal(err)
	}

	updated, err := s.Update(b.ID, bookInput("New", "Author2", 2000, "isbn-x"))
	if err != nil {
		t.Fatalf("update: %v", err)
	}
	if updated.Title != "New" || updated.Author != "Author2" || updated.Year != 2000 {
		t.Fatalf("unexpected updated book: %+v", updated)
	}

	if _, err := s.Update(999, bookInput("x", "y", 0, "")); !errors.Is(err, ErrNotFound) {
		t.Fatalf("expected ErrNotFound on update, got %v", err)
	}

	if err := s.Delete(b.ID); err != nil {
		t.Fatalf("delete: %v", err)
	}
	if err := s.Delete(b.ID); !errors.Is(err, ErrNotFound) {
		t.Fatalf("expected ErrNotFound on second delete, got %v", err)
	}
}
