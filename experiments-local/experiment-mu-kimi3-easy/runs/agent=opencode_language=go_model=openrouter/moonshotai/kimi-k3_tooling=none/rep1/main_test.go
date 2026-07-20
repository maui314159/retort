package main

import (
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// newTestServer returns an httptest server backed by an in-memory SQLite DB.
func newTestServer(t *testing.T) *httptest.Server {
	t.Helper()
	store, err := NewStore(":memory:")
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	srv := httptest.NewServer(NewServer(store))
	t.Cleanup(func() {
		srv.Close()
		store.Close()
	})
	return srv
}

func doJSON(t *testing.T, method, url, body string) (*http.Response, map[string]any) {
	t.Helper()
	var reader *strings.Reader
	if body == "" {
		reader = strings.NewReader("")
	} else {
		reader = strings.NewReader(body)
	}
	req, err := http.NewRequest(method, url, reader)
	if err != nil {
		t.Fatalf("NewRequest: %v", err)
	}
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("%s %s: %v", method, url, err)
	}
	var parsed map[string]any
	if resp.StatusCode != http.StatusNoContent {
		if err := json.NewDecoder(resp.Body).Decode(&parsed); err != nil {
			t.Fatalf("decode response: %v", err)
		}
	}
	resp.Body.Close()
	return resp, parsed
}

func TestHealth(t *testing.T) {
	srv := newTestServer(t)
	resp, body := doJSON(t, "GET", srv.URL+"/health", "")
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("want 200, got %d", resp.StatusCode)
	}
	if body["status"] != "ok" {
		t.Fatalf("want status ok, got %v", body)
	}
}

func TestCreateAndGetBook(t *testing.T) {
	srv := newTestServer(t)

	resp, created := doJSON(t, "POST", srv.URL+"/books",
		`{"title":"The Go Programming Language","author":"Alan Donovan","year":2015,"isbn":"978-0134190440"}`)
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("want 201, got %d (%v)", resp.StatusCode, created)
	}
	if created["id"].(float64) < 1 {
		t.Fatalf("expected assigned id, got %v", created)
	}

	resp, got := doJSON(t, "GET", srv.URL+"/books/1", "")
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("want 200, got %d", resp.StatusCode)
	}
	if got["title"] != "The Go Programming Language" || got["author"] != "Alan Donovan" {
		t.Fatalf("unexpected book: %v", got)
	}
}

func TestCreateBookValidation(t *testing.T) {
	srv := newTestServer(t)

	for _, body := range []string{
		`{"author":"Someone"}`,         // missing title
		`{"title":"Something"}`,        // missing author
		`{"title":"  ","author":"  "}`, // whitespace-only
		`{"title":`,                    // malformed JSON
	} {
		resp, parsed := doJSON(t, "POST", srv.URL+"/books", body)
		if resp.StatusCode != http.StatusBadRequest {
			t.Fatalf("body %q: want 400, got %d (%v)", body, resp.StatusCode, parsed)
		}
		if parsed["error"] == nil || parsed["error"] == "" {
			t.Fatalf("body %q: expected error message, got %v", body, parsed)
		}
	}
}

func TestListBooksWithAuthorFilter(t *testing.T) {
	srv := newTestServer(t)

	for _, b := range []string{
		`{"title":"Book A","author":"Ursula Le Guin","year":1968,"isbn":"1"}`,
		`{"title":"Book B","author":"Ursula Le Guin","year":1969,"isbn":"2"}`,
		`{"title":"Book C","author":"Octavia Butler","year":1993,"isbn":"3"}`,
	} {
		if resp, _ := doJSON(t, "POST", srv.URL+"/books", b); resp.StatusCode != http.StatusCreated {
			t.Fatalf("seed create failed")
		}
	}

	// Unfiltered: 3 books.
	resp, err := http.Get(srv.URL + "/books")
	if err != nil {
		t.Fatal(err)
	}
	var all []map[string]any
	json.NewDecoder(resp.Body).Decode(&all)
	resp.Body.Close()
	if resp.StatusCode != http.StatusOK || len(all) != 3 {
		t.Fatalf("want 3 books, got %d (status %d)", len(all), resp.StatusCode)
	}

	// Filtered: only Le Guin.
	resp, err = http.Get(srv.URL + "/books?author=Ursula+Le+Guin")
	if err != nil {
		t.Fatal(err)
	}
	var filtered []map[string]any
	json.NewDecoder(resp.Body).Decode(&filtered)
	resp.Body.Close()
	if len(filtered) != 2 {
		t.Fatalf("want 2 books for Le Guin, got %d", len(filtered))
	}
	for _, b := range filtered {
		if b["author"] != "Ursula Le Guin" {
			t.Fatalf("filter leaked other author: %v", b)
		}
	}
}

func TestUpdateBook(t *testing.T) {
	srv := newTestServer(t)

	doJSON(t, "POST", srv.URL+"/books", `{"title":"Old Title","author":"Author","year":2000,"isbn":"x"}`)

	resp, updated := doJSON(t, "PUT", srv.URL+"/books/1",
		`{"title":"New Title","author":"Author","year":2001,"isbn":"x"}`)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("want 200, got %d (%v)", resp.StatusCode, updated)
	}
	if updated["title"] != "New Title" || updated["year"].(float64) != 2001 {
		t.Fatalf("update not applied: %v", updated)
	}

	// Update of a missing book -> 404.
	resp, _ = doJSON(t, "PUT", srv.URL+"/books/999",
		`{"title":"X","author":"Y","year":1,"isbn":"z"}`)
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("want 404, got %d", resp.StatusCode)
	}
}

func TestDeleteBook(t *testing.T) {
	srv := newTestServer(t)

	doJSON(t, "POST", srv.URL+"/books", `{"title":"Doomed","author":"A","year":2024,"isbn":"i"}`)

	req, _ := http.NewRequest("DELETE", srv.URL+"/books/1", nil)
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	resp.Body.Close()
	if resp.StatusCode != http.StatusNoContent {
		t.Fatalf("want 204, got %d", resp.StatusCode)
	}

	// Now gone.
	resp, _ = doJSON(t, "GET", srv.URL+"/books/1", "")
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("want 404 after delete, got %d", resp.StatusCode)
	}

	// Deleting again -> 404.
	req, _ = http.NewRequest("DELETE", srv.URL+"/books/1", nil)
	resp, err = http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	resp.Body.Close()
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("want 404 on re-delete, got %d", resp.StatusCode)
	}
}

func TestNotFoundAndBadID(t *testing.T) {
	srv := newTestServer(t)

	resp, _ := doJSON(t, "GET", srv.URL+"/books/42", "")
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("want 404, got %d", resp.StatusCode)
	}

	resp, _ = doJSON(t, "GET", srv.URL+"/books/abc", "")
	if resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("want 400, got %d", resp.StatusCode)
	}
}

func TestStoreRoundTrip(t *testing.T) {
	// Direct store-level test: exercises SQLite persistence without HTTP.
	path := t.TempDir() + "/books.db"
	store, err := NewStore(path)
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	defer store.Close()

	b, err := store.Create(Book{Title: "T", Author: "A", Year: 2020, ISBN: "isbn"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	got, err := store.Get(b.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got != b {
		t.Fatalf("round trip mismatch: %+v vs %+v", got, b)
	}
	if _, err := store.Get(12345); !errors.Is(err, ErrNotFound) {
		t.Fatalf("want ErrNotFound, got %v", err)
	}
}
