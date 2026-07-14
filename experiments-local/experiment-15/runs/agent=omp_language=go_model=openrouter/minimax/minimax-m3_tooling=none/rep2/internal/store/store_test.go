package store_test

import (
	"context"
	"errors"
	"path/filepath"
	"sort"
	"testing"

	"books/internal/book"
	"books/internal/store"
)

// newTestStore returns a Store backed by a fresh in-memory-ish SQLite file
// under t.TempDir(). Each test gets its own file so they can run in parallel
// without trampling each other.
func newTestStore(t *testing.T) *store.Store {
	t.Helper()
	dir := t.TempDir()
	s, err := store.Open(filepath.Join(dir, "test.db"))
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	t.Cleanup(func() { _ = s.Close() })
	return s
}

func TestCreateAndGet(t *testing.T) {
	t.Parallel()
	s := newTestStore(t)
	ctx := context.Background()

	in := book.Input{Title: "The Pragmatic Programmer", Author: "Andy Hunt", Year: 1999, ISBN: "978-0201616224"}
	created, err := s.Create(ctx, in)
	if err != nil {
		t.Fatalf("create: %v", err)
	}
	if created.ID <= 0 {
		t.Fatalf("expected positive ID, got %d", created.ID)
	}
	if created.Title != in.Title || created.Author != in.Author {
		t.Fatalf("round-trip mismatch: %+v", created)
	}

	got, err := s.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("get: %v", err)
	}
	if got != created {
		t.Fatalf("get returned %+v, want %+v", got, created)
	}
}

func TestGetNotFound(t *testing.T) {
	t.Parallel()
	s := newTestStore(t)
	_, err := s.Get(context.Background(), 9999)
	if !errors.Is(err, store.ErrNotFound) {
		t.Fatalf("expected ErrNotFound, got %v", err)
	}
}

func TestListAndFilter(t *testing.T) {
	t.Parallel()
	s := newTestStore(t)
	ctx := context.Background()

	// Insert in non-alphabetical order to make sure list ordering is by ID
	// (insertion order) and not coincidentally alphabetical.
	seed := []book.Input{
		{Title: "Refactoring", Author: "Martin Fowler", Year: 1999, ISBN: "0201485672"},
		{Title: "Patterns of Enterprise Application Architecture", Author: "Martin Fowler", Year: 2002, ISBN: "0321127420"},
		{Title: "Effective Go", Author: "The Go Team", Year: 2020, ISBN: ""},
	}
	wantIDs := make([]int64, 0, len(seed))
	for _, in := range seed {
		b, err := s.Create(ctx, in)
		if err != nil {
			t.Fatalf("create %q: %v", in.Title, err)
		}
		wantIDs = append(wantIDs, b.ID)
	}

	all, err := s.List(ctx, "")
	if err != nil {
		t.Fatalf("list all: %v", err)
	}
	if len(all) != len(seed) {
		t.Fatalf("list all: got %d books, want %d", len(all), len(seed))
	}
	for i, b := range all {
		if b.ID != wantIDs[i] {
			t.Fatalf("list all: position %d has ID %d, want %d", i, b.ID, wantIDs[i])
		}
	}

	filtered, err := s.List(ctx, "fowler")
	if err != nil {
		t.Fatalf("list fowler: %v", err)
	}
	if len(filtered) != 2 {
		t.Fatalf("list fowler: got %d books, want 2", len(filtered))
	}
	// Every returned book must be Fowler's, and the filter is
	// case-insensitive.
	for _, b := range filtered {
		if b.Author != "Martin Fowler" {
			t.Fatalf("filter leak: %+v", b)
		}
	}
	// Sanity: case-insensitive match returns the same result.
	upper, err := s.List(ctx, "FOWLER")
	if err != nil {
		t.Fatalf("list FOWLER: %v", err)
	}
	if len(upper) != len(filtered) {
		t.Fatalf("case-insensitive filter mismatch: lower=%d upper=%d", len(filtered), len(upper))
	}

	// Whitespace-only filter is treated as "no filter" — clients should not
	// have to URL-encode an empty string to get everything.
	ws, err := s.List(ctx, "   ")
	if err != nil {
		t.Fatalf("list whitespace: %v", err)
	}
	if len(ws) != len(seed) {
		t.Fatalf("whitespace filter: got %d, want %d", len(ws), len(seed))
	}
}

func TestListEmpty(t *testing.T) {
	t.Parallel()
	s := newTestStore(t)
	got, err := s.List(context.Background(), "")
	if err != nil {
		t.Fatalf("list empty: %v", err)
	}
	// The store returns a nil slice when there are no rows; the API layer
	// is responsible for converting that to [] for the wire. The contract
	// here is just "no error, zero or one books".
	if len(got) != 0 {
		t.Fatalf("list empty: got %d books, want 0", len(got))
	}
}

func TestUpdate(t *testing.T) {
	t.Parallel()
	s := newTestStore(t)
	ctx := context.Background()

	created, err := s.Create(ctx, book.Input{Title: "Old", Author: "A", Year: 2000})
	if err != nil {
		t.Fatalf("create: %v", err)
	}

	updated, err := s.Update(ctx, created.ID, book.Input{Title: "New", Author: "A", Year: 2001, ISBN: "x"})
	if err != nil {
		t.Fatalf("update: %v", err)
	}
	if updated.Title != "New" || updated.Year != 2001 || updated.ISBN != "x" {
		t.Fatalf("update did not apply: %+v", updated)
	}
	if updated.ID != created.ID {
		t.Fatalf("update changed ID: %d -> %d", created.ID, updated.ID)
	}

	// Update on a missing ID returns ErrNotFound.
	_, err = s.Update(ctx, 9999, book.Input{Title: "X", Author: "Y"})
	if !errors.Is(err, store.ErrNotFound) {
		t.Fatalf("expected ErrNotFound on missing update, got %v", err)
	}
}

func TestDelete(t *testing.T) {
	t.Parallel()
	s := newTestStore(t)
	ctx := context.Background()

	created, err := s.Create(ctx, book.Input{Title: "Doomed", Author: "A"})
	if err != nil {
		t.Fatalf("create: %v", err)
	}
	if err := s.Delete(ctx, created.ID); err != nil {
		t.Fatalf("delete: %v", err)
	}
	if _, err := s.Get(ctx, created.ID); !errors.Is(err, store.ErrNotFound) {
		t.Fatalf("expected ErrNotFound after delete, got %v", err)
	}
	// Second delete is also a not-found; deletes are idempotent at the
	// store-error level even though the row is already gone.
	if err := s.Delete(ctx, created.ID); !errors.Is(err, store.ErrNotFound) {
		t.Fatalf("second delete: expected ErrNotFound, got %v", err)
	}
}

func TestNormalizeOnPersist(t *testing.T) {
	t.Parallel()
	// A simple sanity check that the book package is reachable and behaves
	// the way the store relies on. This is here mostly to catch a future
	// refactor that breaks the store's contract with the domain layer.
	in := book.Input{Title: "  Trim Me  ", Author: "\tAuthor\t", Year: 2024}
	n := in.Normalize()
	if n.Title != "Trim Me" || n.Author != "Author" {
		t.Fatalf("Normalize: %+v", n)
	}
}

// sort is imported to silence an unused-import warning if all the tests
// above ever get refactored to drop sort. The current tests don't use it
// directly, but keeping the import makes future re-ordering tests easier.
var _ = sort.Slice
