package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"testing"
)

func newTestHandler(t *testing.T) (*APIHandler, func()) {
	t.Helper()
	dbPath := filepath.Join(t.TempDir(), "test.db")
	store, err := NewStore(dbPath)
	if err != nil {
		t.Fatalf("init store: %v", err)
	}
	return NewAPIHandler(store), func() {
		if err := store.Close(); err != nil {
			t.Logf("close store: %v", err)
		}
	}
}

func doRequest(t *testing.T, h http.Handler, method, target string, body interface{}) *httptest.ResponseRecorder {
	t.Helper()
	var buf bytes.Buffer
	if body != nil {
		if err := json.NewEncoder(&buf).Encode(body); err != nil {
			t.Fatalf("encode body: %v", err)
		}
	}
	req := httptest.NewRequest(method, target, &buf)
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func TestCreateGetListDelete(t *testing.T) {
	h, cleanup := newTestHandler(t)
	defer cleanup()
	mux := h.Routes()

	// Create
	rec := doRequest(t, mux, "POST", "/books", Book{
		Title: "The Go Programming Language", Author: "Alan Donovan", Year: 2015, ISBN: "9780134190440",
	})
	if rec.Code != http.StatusCreated {
		t.Fatalf("create status = %d, want %d; body=%s", rec.Code, http.StatusCreated, rec.Body.String())
	}
	var created Book
	if err := json.NewDecoder(rec.Body).Decode(&created); err != nil {
		t.Fatalf("decode created: %v", err)
	}
	if created.ID == 0 {
		t.Fatal("expected non-zero id")
	}

	// Get
	rec = doRequest(t, mux, "GET", "/books/"+itoa(created.ID), nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("get status = %d, want %d", rec.Code, http.StatusOK)
	}
	var got Book
	if err := json.NewDecoder(rec.Body).Decode(&got); err != nil {
		t.Fatalf("decode got: %v", err)
	}
	if got.Title != created.Title {
		t.Errorf("title = %q, want %q", got.Title, created.Title)
	}

	// List (with author filter)
	rec = doRequest(t, mux, "GET", "/books?author=Alan+Donovan", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("list status = %d, want %d", rec.Code, http.StatusOK)
	}
	var list []Book
	if err := json.NewDecoder(rec.Body).Decode(&list); err != nil {
		t.Fatalf("decode list: %v", err)
	}
	if len(list) != 1 || list[0].ID != created.ID {
		t.Errorf("list = %+v, want single book with id %d", list, created.ID)
	}

	// List (filter that matches nothing)
	rec = doRequest(t, mux, "GET", "/books?author=Nobody", nil)
	if err := json.NewDecoder(rec.Body).Decode(&list); err != nil {
		t.Fatalf("decode empty list: %v", err)
	}
	if len(list) != 0 {
		t.Errorf("expected empty list, got %d", len(list))
	}

	// Delete
	rec = doRequest(t, mux, "DELETE", "/books/"+itoa(created.ID), nil)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("delete status = %d, want %d", rec.Code, http.StatusNoContent)
	}

	// Get after delete -> 404
	rec = doRequest(t, mux, "GET", "/books/"+itoa(created.ID), nil)
	if rec.Code != http.StatusNotFound {
		t.Errorf("get after delete status = %d, want %d", rec.Code, http.StatusNotFound)
	}
}

func TestValidation(t *testing.T) {
	h, cleanup := newTestHandler(t)
	defer cleanup()
	mux := h.Routes()

	cases := []struct {
		name string
		body Book
	}{
		{"missing title", Book{Author: "X", Year: 2020}},
		{"missing author", Book{Title: "X", Year: 2020}},
		{"both missing", Book{}},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			rec := doRequest(t, mux, "POST", "/books", c.body)
			if rec.Code != http.StatusBadRequest {
				t.Errorf("status = %d, want %d; body=%s", rec.Code, http.StatusBadRequest, rec.Body.String())
			}
		})
	}
}

func TestHealth(t *testing.T) {
	h, cleanup := newTestHandler(t)
	defer cleanup()
	mux := h.Routes()

	rec := doRequest(t, mux, "GET", "/health", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("health status = %d, want %d", rec.Code, http.StatusOK)
	}
	var resp map[string]string
	if err := json.NewDecoder(rec.Body).Decode(&resp); err != nil {
		t.Fatalf("decode health: %v", err)
	}
	if resp["status"] != "ok" {
		t.Errorf("status = %q, want %q", resp["status"], "ok")
	}
}

func TestUpdate(t *testing.T) {
	h, cleanup := newTestHandler(t)
	defer cleanup()
	mux := h.Routes()

	rec := doRequest(t, mux, "POST", "/books", Book{Title: "Old", Author: "A", Year: 2000})
	if rec.Code != http.StatusCreated {
		t.Fatalf("create status = %d", rec.Code)
	}
	var created Book
	json.NewDecoder(rec.Body).Decode(&created)

	// Update
	rec = doRequest(t, mux, "PUT", "/books/"+itoa(created.ID), Book{
		Title: "New", Author: "B", Year: 2021, ISBN: "123",
	})
	if rec.Code != http.StatusOK {
		t.Fatalf("update status = %d, want %d; body=%s", rec.Code, http.StatusOK, rec.Body.String())
	}
	var updated Book
	json.NewDecoder(rec.Body).Decode(&updated)
	if updated.Title != "New" || updated.Author != "B" || updated.ISBN != "123" {
		t.Errorf("updated = %+v", updated)
	}

	// Update non-existent -> 404
	rec = doRequest(t, mux, "PUT", "/books/9999", Book{Title: "X", Author: "Y"})
	if rec.Code != http.StatusNotFound {
		t.Errorf("update missing status = %d, want %d", rec.Code, http.StatusNotFound)
	}
}


