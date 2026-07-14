package main

import (
	"errors"
	"path/filepath"
	"testing"
)

func newTestStore(t *testing.T) *SQLiteStore {
	t.Helper()
	dir := t.TempDir()
	store, err := NewSQLiteStore(filepath.Join(dir, "test.db"))
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	t.Cleanup(func() { _ = store.Close() })
	return store
}

func TestSQLiteStore_CRUD(t *testing.T) {
	store := newTestStore(t)

	// Create
	b := &Book{Title: "The Go Programming Language", Author: "Donovan", Year: 2015, ISBN: "9780134190440"}
	if err := store.Create(b); err != nil {
		t.Fatalf("create: %v", err)
	}
	if b.ID == 0 {
		t.Fatal("expected non-zero id after create")
	}

	// Get
	got, err := store.Get(b.ID)
	if err != nil {
		t.Fatalf("get: %v", err)
	}
	if got.Title != b.Title || got.Author != b.Author || got.Year != b.Year || got.ISBN != b.ISBN {
		t.Fatalf("get returned mismatched book: %+v", got)
	}

	// Update
	got.Title = "Updated Title"
	got.Year = 2020
	updated, err := store.Update(got.ID, got)
	if err != nil {
		t.Fatalf("update: %v", err)
	}
	if updated.Title != "Updated Title" || updated.Year != 2020 {
		t.Fatalf("update did not persist: %+v", updated)
	}

	// List with author filter
	other := &Book{Title: "Another", Author: "Kernighan", Year: 2018, ISBN: "111"}
	if err := store.Create(other); err != nil {
		t.Fatalf("create other: %v", err)
	}

	all, err := store.List("")
	if err != nil {
		t.Fatalf("list all: %v", err)
	}
	if len(all) != 2 {
		t.Fatalf("expected 2 books, got %d", len(all))
	}

	filtered, err := store.List("Kernighan")
	if err != nil {
		t.Fatalf("list filtered: %v", err)
	}
	if len(filtered) != 1 || filtered[0].ID != other.ID {
		t.Fatalf("filter mismatch: %+v", filtered)
	}

	// Delete
	if err := store.Delete(b.ID); err != nil {
		t.Fatalf("delete: %v", err)
	}
	if _, err := store.Get(b.ID); !errors.Is(err, ErrNotFound) {
		t.Fatalf("expected ErrNotFound after delete, got %v", err)
	}

	// Delete missing -> ErrNotFound
	if err := store.Delete(b.ID); !errors.Is(err, ErrNotFound) {
		t.Fatalf("expected ErrNotFound deleting missing, got %v", err)
	}

	// Update missing -> ErrNotFound
	if _, err := store.Update(b.ID, &Book{Title: "x", Author: "y"}); !errors.Is(err, ErrNotFound) {
		t.Fatalf("expected ErrNotFound updating missing, got %v", err)
	}
}
