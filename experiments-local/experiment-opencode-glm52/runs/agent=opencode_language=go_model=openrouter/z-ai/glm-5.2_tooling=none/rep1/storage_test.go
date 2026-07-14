package main

import (
	"path/filepath"
	"testing"
)

func TestStoreCRUD(t *testing.T) {
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "store.db")
	s, err := NewStore(dbPath)
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	defer s.Close()

	created, err := s.Create(Book{Title: "Title", Author: "Author", Year: 1990, ISBN: "abc"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if created.ID == 0 {
		t.Fatal("expected nonzero id")
	}

	got, err := s.Get(created.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got.Title != "Title" || got.Author != "Author" || got.Year != 1990 || got.ISBN != "abc" {
		t.Fatalf("got = %+v", got)
	}

	if _, err := s.Get(9999); err == nil {
		t.Fatal("expected error for missing get")
	}

	all, err := s.List("")
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(all) != 1 {
		t.Fatalf("len(all)=%d want 1", len(all))
	}

	// Add another then filter
	if _, err := s.Create(Book{Title: "Other", Author: "SomeoneElse"}); err != nil {
		t.Fatalf("Create 2: %v", err)
	}
	byAuthor, err := s.List("Author")
	if err != nil {
		t.Fatalf("List filter: %v", err)
	}
	if len(byAuthor) != 1 || byAuthor[0].Author != "Author" {
		t.Fatalf("byAuthor=%+v", byAuthor)
	}

	updated, err := s.Update(created.ID, Book{Title: "New", Author: "NewA", Year: 2000})
	if err != nil {
		t.Fatalf("Update: %v", err)
	}
	if updated.Title != "New" {
		t.Fatalf("updated=%+v", updated)
	}
	if _, err := s.Update(9999, Book{Title: "X", Author: "Y"}); err == nil {
		t.Fatal("expected error for missing update")
	}

	if err := s.Delete(created.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if err := s.Delete(created.ID); err == nil {
		t.Fatal("expected error for deleting missing")
	}
}

func TestStoreValidationInvariants(t *testing.T) {
	dir := t.TempDir()
	s, err := NewStore(filepath.Join(dir, "v.db"))
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	defer s.Close()
	// Validate at model layer
	if (Book{}).Validate() != "title is required" {
		t.Fatal("expected title required first")
	}
	if (Book{Author: "a"}).Validate() != "title is required" {
		t.Fatal("expected title required")
	}
	if (Book{Title: "t", Author: "a"}).Validate() != "" {
		t.Fatal("expected valid")
	}
	if (Book{Title: "t", Author: "a", Year: -1}).Validate() != "year must be a non-negative integer" {
		t.Fatal("expected year error")
	}
}
