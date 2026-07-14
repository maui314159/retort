package book

import (
	"context"
	"path/filepath"
	"testing"
)

func newTestStore(t *testing.T) *Store {
	t.Helper()
	dir := t.TempDir()
	store, err := NewStore(context.Background(), filepath.Join(dir, "test.db"))
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return store
}

func TestCreateAndGet(t *testing.T) {
	store := newTestStore(t)
	ctx := context.Background()

	b, err := store.Create(ctx, Book{Title: "The Go Programming Language", Author: "Donovan", Year: 2015, ISBN: "9780134190440"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if b.ID == 0 {
		t.Fatal("expected non-zero ID")
	}

	got, err := store.Get(ctx, b.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got.Title != "The Go Programming Language" || got.Author != "Donovan" {
		t.Fatalf("unexpected book: %+v", got)
	}
}

func TestCreateValidation(t *testing.T) {
	store := newTestStore(t)
	ctx := context.Background()

	cases := []Book{
		{Title: "", Author: "A"},              // missing title
		{Title: "T", Author: ""},              // missing author
		{Title: "T", Author: "A", ISBN: "X"},  // bad isbn
		{Title: "T", Author: "A", Year: 3000}, // future year
	}
	for i, c := range cases {
		if _, err := store.Create(ctx, c); !IsValidation(err) {
			t.Fatalf("case %d: expected validation error, got %v", i, err)
		}
	}
}

func TestListAuthorFilter(t *testing.T) {
	store := newTestStore(t)
	ctx := context.Background()

	seed := []Book{
		{Title: "A", Author: "Alice"},
		{Title: "B", Author: "Bob"},
		{Title: "C", Author: "Alice"},
	}
	for _, b := range seed {
		if _, err := store.Create(ctx, b); err != nil {
			t.Fatalf("Create: %v", err)
		}
	}

	all, err := store.List(ctx, "")
	if err != nil {
		t.Fatalf("List all: %v", err)
	}
	if len(all) != 3 {
		t.Fatalf("expected 3 books, got %d", len(all))
	}

	alice, err := store.List(ctx, "Alice")
	if err != nil {
		t.Fatalf("List Alice: %v", err)
	}
	if len(alice) != 2 {
		t.Fatalf("expected 2 Alice books, got %d", len(alice))
	}
}

func TestUpdateAndDelete(t *testing.T) {
	store := newTestStore(t)
	ctx := context.Background()

	b, err := store.Create(ctx, Book{Title: "Old", Author: "A"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}

	updated, err := store.Update(ctx, b.ID, Book{Title: "New", Author: "A", Year: 2020})
	if err != nil {
		t.Fatalf("Update: %v", err)
	}
	if updated.Title != "New" || updated.Year != 2020 {
		t.Fatalf("unexpected update: %+v", updated)
	}

	if err := store.Delete(ctx, b.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if _, err := store.Get(ctx, b.ID); err != ErrNotFound {
		t.Fatalf("expected ErrNotFound after delete, got %v", err)
	}

	// Delete again -> not found.
	if err := store.Delete(ctx, b.ID); err != ErrNotFound {
		t.Fatalf("expected ErrNotFound on re-delete, got %v", err)
	}

	// Update missing -> not found.
	if _, err := store.Update(ctx, 9999, Book{Title: "X", Author: "Y"}); err != ErrNotFound {
		t.Fatalf("expected ErrNotFound on missing update, got %v", err)
	}
}

// IsValidation reports whether err is the validation sentinel.
func IsValidation(err error) bool { return err == ErrValidation }
