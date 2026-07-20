package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"
)

// newTestServer spins up an httptest server backed by a private in-memory
// SQLite database (unique per test name).
func newTestServer(t *testing.T) *httptest.Server {
	t.Helper()
	dsn := fmt.Sprintf("file:%s?mode=memory&cache=shared", t.Name())
	store, err := NewStore(dsn)
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

func post(t *testing.T, url string, body string) *http.Response {
	t.Helper()
	resp, err := http.Post(url, "application/json", bytes.NewBufferString(body))
	if err != nil {
		t.Fatalf("POST %s: %v", url, err)
	}
	return resp
}

func decodeBook(t *testing.T, resp *http.Response) Book {
	t.Helper()
	var b Book
	if err := json.NewDecoder(resp.Body).Decode(&b); err != nil {
		t.Fatalf("decode book: %v", err)
	}
	resp.Body.Close()
	return b
}

func TestHealth(t *testing.T) {
	srv := newTestServer(t)
	resp, err := http.Get(srv.URL + "/health")
	if err != nil {
		t.Fatalf("GET /health: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("status = %d, want 200", resp.StatusCode)
	}
	var body map[string]string
	if err := json.NewDecoder(resp.Body).Decode(&body); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if body["status"] != "ok" {
		t.Fatalf("status body = %q, want %q", body["status"], "ok")
	}
}

func TestCreateAndGetBook(t *testing.T) {
	srv := newTestServer(t)

	resp := post(t, srv.URL+"/books",
		`{"title":"The Go Programming Language","author":"Alan Donovan","year":2015,"isbn":"978-0134190440"}`)
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("create status = %d, want 201", resp.StatusCode)
	}
	created := decodeBook(t, resp)
	if created.ID == 0 {
		t.Fatal("created book has no ID")
	}
	if created.Title != "The Go Programming Language" || created.Author != "Alan Donovan" {
		t.Fatalf("unexpected created book: %+v", created)
	}

	resp2, err := http.Get(fmt.Sprintf("%s/books/%d", srv.URL, created.ID))
	if err != nil {
		t.Fatalf("GET /books/{id}: %v", err)
	}
	if resp2.StatusCode != http.StatusOK {
		t.Fatalf("get status = %d, want 200", resp2.StatusCode)
	}
	got := decodeBook(t, resp2)
	if got != created {
		t.Fatalf("got %+v, want %+v", got, created)
	}
}

func TestCreateBookValidation(t *testing.T) {
	srv := newTestServer(t)

	cases := []struct {
		name string
		body string
	}{
		{"missing title", `{"author":"X","year":2020}`},
		{"missing author", `{"title":"Y","year":2020}`},
		{"empty title", `{"title":"  ","author":"X"}`},
		{"invalid json", `{"title":`},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			resp := post(t, srv.URL+"/books", tc.body)
			defer resp.Body.Close()
			if resp.StatusCode != http.StatusBadRequest {
				t.Fatalf("status = %d, want 400", resp.StatusCode)
			}
			var body map[string]string
			if err := json.NewDecoder(resp.Body).Decode(&body); err != nil {
				t.Fatalf("decode: %v", err)
			}
			if body["error"] == "" {
				t.Fatal("expected error message in response")
			}
		})
	}
}

func TestListBooksWithAuthorFilter(t *testing.T) {
	srv := newTestServer(t)

	books := []string{
		`{"title":"Book A","author":"Alice","year":2001}`,
		`{"title":"Book B","author":"Bob","year":2002}`,
		`{"title":"Book C","author":"Alice","year":2003}`,
	}
	for _, b := range books {
		resp := post(t, srv.URL+"/books", b)
		if resp.StatusCode != http.StatusCreated {
			t.Fatalf("seed create status = %d", resp.StatusCode)
		}
		resp.Body.Close()
	}

	resp, err := http.Get(srv.URL + "/books")
	if err != nil {
		t.Fatalf("GET /books: %v", err)
	}
	var all []Book
	if err := json.NewDecoder(resp.Body).Decode(&all); err != nil {
		t.Fatalf("decode: %v", err)
	}
	resp.Body.Close()
	if len(all) != 3 {
		t.Fatalf("list returned %d books, want 3", len(all))
	}

	resp2, err := http.Get(srv.URL + "/books?author=Alice")
	if err != nil {
		t.Fatalf("GET /books?author=Alice: %v", err)
	}
	var filtered []Book
	if err := json.NewDecoder(resp2.Body).Decode(&filtered); err != nil {
		t.Fatalf("decode: %v", err)
	}
	resp2.Body.Close()
	if len(filtered) != 2 {
		t.Fatalf("filtered list returned %d books, want 2", len(filtered))
	}
	for _, b := range filtered {
		if b.Author != "Alice" {
			t.Fatalf("filtered book has author %q, want Alice", b.Author)
		}
	}
}

func TestUpdateBook(t *testing.T) {
	srv := newTestServer(t)

	resp := post(t, srv.URL+"/books", `{"title":"Old","author":"A","year":1999}`)
	created := decodeBook(t, resp)

	req, err := http.NewRequest(http.MethodPut,
		fmt.Sprintf("%s/books/%d", srv.URL, created.ID),
		bytes.NewBufferString(`{"title":"New","author":"B","year":2024,"isbn":"123"}`))
	if err != nil {
		t.Fatal(err)
	}
	req.Header.Set("Content-Type", "application/json")
	resp2, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("PUT: %v", err)
	}
	if resp2.StatusCode != http.StatusOK {
		t.Fatalf("update status = %d, want 200", resp2.StatusCode)
	}
	updated := decodeBook(t, resp2)
	if updated.ID != created.ID || updated.Title != "New" || updated.Author != "B" ||
		updated.Year != 2024 || updated.ISBN != "123" {
		t.Fatalf("unexpected updated book: %+v", updated)
	}

	// Update of a non-existent book must 404.
	req3, _ := http.NewRequest(http.MethodPut, srv.URL+"/books/9999",
		bytes.NewBufferString(`{"title":"X","author":"Y"}`))
	req3.Header.Set("Content-Type", "application/json")
	resp3, err := http.DefaultClient.Do(req3)
	if err != nil {
		t.Fatalf("PUT missing: %v", err)
	}
	resp3.Body.Close()
	if resp3.StatusCode != http.StatusNotFound {
		t.Fatalf("update missing status = %d, want 404", resp3.StatusCode)
	}
}

func TestDeleteBook(t *testing.T) {
	srv := newTestServer(t)

	resp := post(t, srv.URL+"/books", `{"title":"Doomed","author":"A"}`)
	created := decodeBook(t, resp)

	req, _ := http.NewRequest(http.MethodDelete,
		fmt.Sprintf("%s/books/%d", srv.URL, created.ID), nil)
	resp2, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("DELETE: %v", err)
	}
	resp2.Body.Close()
	if resp2.StatusCode != http.StatusNoContent {
		t.Fatalf("delete status = %d, want 204", resp2.StatusCode)
	}

	// The book must be gone.
	resp3, err := http.Get(fmt.Sprintf("%s/books/%d", srv.URL, created.ID))
	if err != nil {
		t.Fatalf("GET deleted: %v", err)
	}
	resp3.Body.Close()
	if resp3.StatusCode != http.StatusNotFound {
		t.Fatalf("get deleted status = %d, want 404", resp3.StatusCode)
	}

	// Deleting it again must also 404.
	req4, _ := http.NewRequest(http.MethodDelete,
		fmt.Sprintf("%s/books/%d", srv.URL, created.ID), nil)
	resp4, err := http.DefaultClient.Do(req4)
	if err != nil {
		t.Fatalf("DELETE again: %v", err)
	}
	resp4.Body.Close()
	if resp4.StatusCode != http.StatusNotFound {
		t.Fatalf("delete again status = %d, want 404", resp4.StatusCode)
	}
}

func TestGetBookNotFound(t *testing.T) {
	srv := newTestServer(t)

	resp, err := http.Get(srv.URL + "/books/42")
	if err != nil {
		t.Fatalf("GET: %v", err)
	}
	resp.Body.Close()
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("status = %d, want 404", resp.StatusCode)
	}

	resp2, err := http.Get(srv.URL + "/books/notanumber")
	if err != nil {
		t.Fatalf("GET invalid id: %v", err)
	}
	resp2.Body.Close()
	if resp2.StatusCode != http.StatusBadRequest {
		t.Fatalf("invalid id status = %d, want 400", resp2.StatusCode)
	}
}
