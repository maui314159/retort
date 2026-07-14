package main

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strconv"
	"testing"

	"github.com/gorilla/mux"
)

func newTestStore(t *testing.T) (*Store, func()) {
	t.Helper()
	dir := t.TempDir()
	path := filepath.Join(dir, "test.db")
	s, err := NewStore(path)
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	cleanup := func() {
		_ = s.Close()
		_ = os.RemoveAll(dir)
	}
	return s, cleanup
}

func mustCreate(t *testing.T, s *Store, title, author, isbn string, year int) Book {
	t.Helper()
	y := year
	b := Book{Title: title, Author: author, ISBN: isbn, Year: &y}
	got, err := s.Create(b)
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	return got
}

// --- Unit tests -----------------------------------------------------------

func TestBookInputValidation(t *testing.T) {
	t.Parallel()
	title := "T"
	author := "A"
	zero := 0
	big := 9999
	huge := 10000
	long := make([]byte, 33)

	cases := []struct {
		name string
		in   bookInput
		want int // number of error fields
	}{
		{"missing title", bookInput{Author: &author}, 1},
		{"empty title", bookInput{Title: ptr("  "), Author: &author}, 1},
		{"missing author", bookInput{Title: &title}, 1},
		{"empty author", bookInput{Title: &title, Author: ptr(" ")}, 1},
		{"valid minimal", bookInput{Title: &title, Author: &author}, 0},
		{"year zero valid", bookInput{Title: &title, Author: &author, Year: &zero}, 0},
		{"year max valid", bookInput{Title: &title, Author: &author, Year: &big}, 0},
		{"year too big", bookInput{Title: &title, Author: &author, Year: &huge}, 1},
		{"year negative", bookInput{Title: &title, Author: &author, Year: intPtr(-1)}, 1},
		{"isbn too long", bookInput{Title: &title, Author: &author, ISBN: ptr(string(long))}, 1},
		{"isbn valid", bookInput{Title: &title, Author: &author, ISBN: ptr("9783161488416")}, 0},
	}
	for _, tc := range cases {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			errs := tc.in.validate()
			if len(errs) != tc.want {
				t.Fatalf("got %d errors (%v), want %d", len(errs), errs, tc.want)
			}
		})
	}
}

func TestStoreCreateGetDelete(t *testing.T) {
	s, cleanup := newTestStore(t)
	defer cleanup()

	b := mustCreate(t, s, "Refactoring", "Martin Fowler", "0-201-48567-2", 1999)
	if b.ID < 1 {
		t.Fatalf("ID should be positive, got %d", b.ID)
	}
	if b.Title != "Refactoring" {
		t.Fatalf("title mismatch: %q", b.Title)
	}
	if b.Year == nil || *b.Year != 1999 {
		t.Fatalf("year mismatch: %v", b.Year)
	}
	if b.ISBN != "0-201-48567-2" {
		t.Fatalf("isbn mismatch: %q", b.ISBN)
	}

	got, err := s.Get(b.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got.Title != b.Title {
		t.Fatalf("roundtrip title mismatch")
	}
	if _, err := s.Get(99999); err == nil {
		t.Fatalf("expected error for missing book")
	}

	if err := s.Delete(b.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if _, err := s.Get(b.ID); err == nil {
		t.Fatalf("expected error after delete")
	}
}

func TestStoreListAuthorFilter(t *testing.T) {
	s, cleanup := newTestStore(t)
	defer cleanup()

	mustCreate(t, s, "Book A", "Alice", "", 2001)
	mustCreate(t, s, "Book B", "Bob", "", 2002)
	mustCreate(t, s, "Book C", "Alice", "", 2003)

	all, err := s.List("")
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(all) != 3 {
		t.Fatalf("all: got %d, want 3", len(all))
	}

	alice, err := s.List("alice")
	if err != nil {
		t.Fatalf("List alice: %v", err)
	}
	if len(alice) != 2 {
		t.Fatalf("alice: got %d, want 2", len(alice))
	}
	for _, b := range alice {
		if b.Author != "Alice" {
			t.Fatalf("unexpected author %q", b.Author)
		}
	}

	none, err := s.List("nobody")
	if err != nil {
		t.Fatalf("List nobody: %v", err)
	}
	if len(none) != 0 {
		t.Fatalf("none: got %d, want 0", len(none))
	}
}

func TestStoreUpdateMerge(t *testing.T) {
	s, cleanup := newTestStore(t)
	defer cleanup()

	created := mustCreate(t, s, "Old Title", "Old Author", "old-isbn", 2000)

	newTitle := "New Title"
	newYear := 2010
	in := bookInput{Title: &newTitle, Year: &newYear}
	updated, err := s.Update(created.ID, in)
	if err != nil {
		t.Fatalf("Update: %v", err)
	}
	if updated.Title != "New Title" {
		t.Fatalf("title: %q", updated.Title)
	}
	if updated.Author != "Old Author" {
		t.Fatalf("author changed unexpectedly: %q", updated.Author)
	}
	if updated.ISBN != "old-isbn" {
		t.Fatalf("isbn changed unexpectedly: %q", updated.ISBN)
	}
	if updated.Year == nil || *updated.Year != 2010 {
		t.Fatalf("year: %v", updated.Year)
	}
}

// TestBookInputPartialValidation verifies that update-style validation does
// not require fields to be present, but still rejects empty / out-of-range
// values for fields that are supplied.
func TestBookInputPartialValidation(t *testing.T) {
	t.Parallel()
	title := "T"
	author := "A"

	cases := []struct {
		name string
		in   bookInput
		want int
	}{
		{"empty allowed", bookInput{}, 0},
		{"empty title rejected", bookInput{Title: ptr("   ")}, 1},
		{"empty author rejected", bookInput{Author: ptr("   ")}, 1},
		{"valid title only", bookInput{Title: &title}, 0},
		{"valid author only", bookInput{Author: &author}, 0},
		{"bad year rejected", bookInput{Year: intPtr(-1)}, 1},
		{"bad isbn rejected", bookInput{ISBN: ptr("0123456789012345678901234567890123")}, 1},
	}
	for _, tc := range cases {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			errs := tc.in.validatePartial()
			if len(errs) != tc.want {
				t.Fatalf("got %d errors (%v), want %d", len(errs), errs, tc.want)
			}
		})
	}
}

// --- Integration tests ----------------------------------------------------

func TestIntegrationFullLifecycle(t *testing.T) {
	s, cleanup := newTestStore(t)
	defer cleanup()

	srv := httptest.NewServer(Router(s))
	defer srv.Close()

	// Create.
	body := mustMarshal(t, map[string]any{
		"title":  "Clean Code",
		"author": "Robert C. Martin",
		"year":   2008,
		"isbn":   "978-0-13-235088-4",
	})
	resp := do(t, http.MethodPost, srv.URL+"/books", body)
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("create: got %d, want %d", resp.StatusCode, http.StatusCreated)
	}
	var created Book
	mustDecode(t, resp.Body, &created)
	if created.ID < 1 {
		t.Fatalf("no id: %+v", created)
	}

	// Get.
	resp = do(t, http.MethodGet, srv.URL+"/books/"+itoa(created.ID), nil)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("get: %d", resp.StatusCode)
	}
	var got Book
	mustDecode(t, resp.Body, &got)
	if got.Title != created.Title {
		t.Fatalf("title mismatch")
	}

	// List with filter.
	mustCreate(t, s, "Other", "Robert C. Martin", "", 2011)
	mustCreate(t, s, "Unrelated", "Someone Else", "", 2012)
	resp = do(t, http.MethodGet, srv.URL+"/books?author=Robert%20C.%20Martin", nil)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("list: %d", resp.StatusCode)
	}
	var list []Book
	mustDecode(t, resp.Body, &list)
	if len(list) != 2 {
		t.Fatalf("list len: got %d, want 2", len(list))
	}

	// Update.
	updatedTitle := "Clean Code (2nd Edition)"
	updatedYear := 2022
	body = mustMarshal(t, map[string]any{
		"title": updatedTitle,
		"year":  updatedYear,
	})
	resp = do(t, http.MethodPut, srv.URL+"/books/"+itoa(created.ID), body)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("update: %d", resp.StatusCode)
	}
	var updated Book
	mustDecode(t, resp.Body, &updated)
	if updated.Title != updatedTitle {
		t.Fatalf("updated title: %q", updated.Title)
	}
	if updated.Author != "Robert C. Martin" {
		t.Fatalf("author changed: %q", updated.Author)
	}
	if updated.Year == nil || *updated.Year != updatedYear {
		t.Fatalf("updated year: %v", updated.Year)
	}

	// Delete.
	resp = do(t, http.MethodDelete, srv.URL+"/books/"+itoa(created.ID), nil)
	if resp.StatusCode != http.StatusNoContent {
		t.Fatalf("delete: got %d, want %d", resp.StatusCode, http.StatusNoContent)
	}
	resp = do(t, http.MethodGet, srv.URL+"/books/"+itoa(created.ID), nil)
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("after delete: got %d, want %d", resp.StatusCode, http.StatusNotFound)
	}
}

func TestIntegrationValidationAndHealth(t *testing.T) {
	s, cleanup := newTestStore(t)
	defer cleanup()

	srv := httptest.NewServer(Router(s))
	defer srv.Close()

	// Health.
	resp := do(t, http.MethodGet, srv.URL+"/health", nil)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("health: %d", resp.StatusCode)
	}
	var h map[string]string
	mustDecode(t, resp.Body, &h)
	if h["status"] != "ok" {
		t.Fatalf("health body: %+v", h)
	}

	// Missing title.
	body := mustMarshal(t, map[string]any{"author": "Someone"})
	resp = do(t, http.MethodPost, srv.URL+"/books", body)
	if resp.StatusCode != http.StatusUnprocessableEntity {
		t.Fatalf("missing title: got %d, want %d", resp.StatusCode, http.StatusUnprocessableEntity)
	}

	// Empty author.
	body = mustMarshal(t, map[string]any{"title": "T", "author": "   "})
	resp = do(t, http.MethodPost, srv.URL+"/books", body)
	if resp.StatusCode != http.StatusUnprocessableEntity {
		t.Fatalf("empty author: got %d, want %d", resp.StatusCode, http.StatusUnprocessableEntity)
	}

	// Malformed JSON.
	malformed := bytes.NewBufferString("{not json")
	resp = do(t, http.MethodPost, srv.URL+"/books", malformed)
	if resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("malformed: got %d, want %d", resp.StatusCode, http.StatusBadRequest)
	}

	// Invalid id.
	resp = do(t, http.MethodGet, srv.URL+"/books/notanint", nil)
	if resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("bad id: got %d, want %d", resp.StatusCode, http.StatusBadRequest)
	}

	// Unknown book.
	resp = do(t, http.MethodGet, srv.URL+"/books/123456", nil)
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("unknown: got %d, want %d", resp.StatusCode, http.StatusNotFound)
	}
}

// TestIntegrationRouteOrder verifies that the author-query route takes
// precedence over the plain /books route when the query param is present.
func TestIntegrationRouteOrder(t *testing.T) {
	s, cleanup := newTestStore(t)
	defer cleanup()

	// Register routes manually to mirror Router() but with explicit ordering
	// verification via a fresh router.
	r := mux.NewRouter()
	r.HandleFunc("/books", listBooks(s)).Methods(http.MethodGet).Queries("author", "{author}")
	r.HandleFunc("/books", listBooks(s)).Methods(http.MethodGet)
	srv := httptest.NewServer(r)
	defer srv.Close()

	mustCreate(t, s, "A", "Alice", "", 2000)
	mustCreate(t, s, "B", "Bob", "", 2001)

	// With author param.
	resp := do(t, http.MethodGet, srv.URL+"/books?author=Alice", nil)
	var list []Book
	mustDecode(t, resp.Body, &list)
	if len(list) != 1 || list[0].Author != "Alice" {
		t.Fatalf("filter: %+v", list)
	}

	// Without author param.
	resp = do(t, http.MethodGet, srv.URL+"/books", nil)
	mustDecode(t, resp.Body, &list)
	if len(list) != 2 {
		t.Fatalf("all: %+v", list)
	}
}

// --- helpers --------------------------------------------------------------

func ptr(s string) *string { return &s }
func intPtr(i int) *int    { return &i }

func do(t *testing.T, method, url string, body io.Reader) *http.Response {
	t.Helper()
	req, err := http.NewRequest(method, url, body)
	if err != nil {
		t.Fatalf("NewRequest: %v", err)
	}
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("Do: %v", err)
	}
	return resp
}

func mustMarshal(t *testing.T, v any) *bytes.Buffer {
	t.Helper()
	buf := &bytes.Buffer{}
	if err := json.NewEncoder(buf).Encode(v); err != nil {
		t.Fatalf("marshal: %v", err)
	}
	return buf
}

func mustDecode(t *testing.T, body interface{ Read(p []byte) (int, error) }, dst any) {
	t.Helper()
	if err := json.NewDecoder(body).Decode(dst); err != nil {
		t.Fatalf("decode: %v", err)
	}
}

func itoa(n int64) string {
	return strconv.FormatInt(n, 10)
}
