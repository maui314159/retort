package books

import (
	"context"
	"path/filepath"
	"testing"
)

// openTestStore returns a fresh in-memory SQLite store. The schema is
// created on Open, so no additional setup is needed.
func openTestStore(t *testing.T) *SQLiteStore {
	t.Helper()
	s, err := Open(":memory:")
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	t.Cleanup(func() { _ = s.Close() })
	return s
}

// TestStoreCRUD walks Create → Get → List → Update → Delete to make
// sure the happy path works end-to-end against a real SQLite database.
func TestStoreCRUD(t *testing.T) {
	ctx := context.Background()
	s := openTestStore(t)

	// Create
	in := &Book{Title: "The Go Programming Language", Author: "Alan A. A. Donovan", Year: 2015, ISBN: "978-0134190440"}
	if err := s.Create(ctx, in); err != nil {
		t.Fatalf("Create: %v", err)
	}
	if in.ID == 0 {
		t.Fatal("Create did not assign an ID")
	}

	// Get
	got, err := s.Get(ctx, in.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got.Title != in.Title || got.Author != in.Author || got.Year != in.Year || got.ISBN != in.ISBN {
		t.Errorf("Get returned %+v, want %+v", got, in)
	}

	// List (unfiltered)
	all, err := s.List(ctx, "")
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(all) != 1 {
		t.Fatalf("List: got %d books, want 1", len(all))
	}

	// Update
	got.Year = 2016
	got.ISBN = "978-0134190441"
	if err := s.Update(ctx, got.ID, got); err != nil {
		t.Fatalf("Update: %v", err)
	}
	updated, err := s.Get(ctx, got.ID)
	if err != nil {
		t.Fatalf("Get after update: %v", err)
	}
	if updated.Year != 2016 || updated.ISBN != "978-0134190441" {
		t.Errorf("Update did not persist: got %+v", updated)
	}

	// Delete
	if err := s.Delete(ctx, got.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if _, err := s.Get(ctx, got.ID); err != ErrNotFound {
		t.Errorf("Get after delete: got err=%v, want ErrNotFound", err)
	}
}

// TestStoreListByAuthor verifies the ?author= filter returns only
// matching rows and is case-sensitive (matches the SQL `=` semantics).
func TestStoreListByAuthor(t *testing.T) {
	ctx := context.Background()
	s := openTestStore(t)

	books := []*Book{
		{Title: "B1", Author: "Alice"},
		{Title: "B2", Author: "Bob"},
		{Title: "B3", Author: "Alice"},
	}
	for _, b := range books {
		if err := s.Create(ctx, b); err != nil {
			t.Fatalf("Create: %v", err)
		}
	}

	got, err := s.List(ctx, "Alice")
	if err != nil {
		t.Fatalf("List(Alice): %v", err)
	}
	if len(got) != 2 {
		t.Fatalf("List(Alice): got %d, want 2", len(got))
	}
	for _, b := range got {
		if b.Author != "Alice" {
			t.Errorf("List(Alice) returned non-Alice book: %+v", b)
		}
	}

	none, err := s.List(ctx, "Carol")
	if err != nil {
		t.Fatalf("List(Carol): %v", err)
	}
	if len(none) != 0 {
		t.Errorf("List(Carol): got %d, want 0", len(none))
	}
}

// TestStoreNotFound confirms Get/Update/Delete return ErrNotFound for
// IDs that don't exist, rather than some other opaque error.
func TestStoreNotFound(t *testing.T) {
	ctx := context.Background()
	s := openTestStore(t)

	if _, err := s.Get(ctx, 999); err != ErrNotFound {
		t.Errorf("Get missing: got err=%v, want ErrNotFound", err)
	}
	if err := s.Update(ctx, 999, &Book{Title: "x", Author: "y"}); err != ErrNotFound {
		t.Errorf("Update missing: got err=%v, want ErrNotFound", err)
	}
	if err := s.Delete(ctx, 999); err != ErrNotFound {
		t.Errorf("Delete missing: got err=%v, want ErrNotFound", err)
	}
}

// TestStoreFilePersistence sanity-checks that data actually round-trips
// through a real on-disk file (not just :memory:), so the production
// configuration is exercised by the test suite.
func TestStoreFilePersistence(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "books.db")

	s1, err := Open(path)
	if err != nil {
		t.Fatalf("Open #1: %v", err)
	}
	if err := s1.Create(context.Background(), &Book{Title: "T", Author: "A"}); err != nil {
		t.Fatalf("Create: %v", err)
	}
	if err := s1.Close(); err != nil {
		t.Fatalf("Close #1: %v", err)
	}

	s2, err := Open(path)
	if err != nil {
		t.Fatalf("Open #2: %v", err)
	}
	defer s2.Close()

	got, err := s2.List(context.Background(), "")
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(got) != 1 || got[0].Title != "T" {
		t.Errorf("persistence: got %+v, want one book with title T", got)
	}
}
