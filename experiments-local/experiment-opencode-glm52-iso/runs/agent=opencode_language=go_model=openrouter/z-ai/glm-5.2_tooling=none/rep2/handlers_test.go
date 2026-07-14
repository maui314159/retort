package main

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// newTestAPI spins up an API backed by an in-memory SQLite database.
func newTestAPI(t *testing.T) (*API, func()) {
	t.Helper()
	store, err := NewStorage("", true)
	if err != nil {
		t.Fatalf("open storage: %v", err)
	}
	api := NewAPI(store)
	cleanup := func() {
		_ = store.Close()
	}
	return api, cleanup
}

func doRequest(t *testing.T, h http.Handler, method, target string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var r io.Reader
	if body != nil {
		b, err := json.Marshal(body)
		if err != nil {
			t.Fatalf("marshal body: %v", err)
		}
		r = bytes.NewReader(b)
	}
	req := httptest.NewRequest(method, target, r)
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func TestCreateBookValidation(t *testing.T) {
	api, cleanup := newTestAPI(t)
	defer cleanup()
	h := api.Routes()

	cases := []struct {
		name       string
		payload    map[string]any
		wantStatus int
		wantSubstr string
	}{
		{"missing title", map[string]any{"author": "Alice"}, http.StatusBadRequest, "title"},
		{"missing author", map[string]any{"title": "T"}, http.StatusBadRequest, "author"},
		{"empty title", map[string]any{"title": "   ", "author": "Alice"}, http.StatusBadRequest, "title"},
		{"negative year", map[string]any{"title": "T", "author": "A", "year": -5}, http.StatusBadRequest, "year"},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			rec := doRequest(t, h, "POST", "/books", c.payload)
			if rec.Code != c.wantStatus {
				t.Fatalf("status = %d, want %d, body=%s", rec.Code, c.wantStatus, rec.Body.String())
			}
			if c.wantSubstr != "" && !strings.Contains(rec.Body.String(), c.wantSubstr) {
				t.Fatalf("body %q does not contain %q", rec.Body.String(), c.wantSubstr)
			}
		})
	}
}

func TestCRUDFlow(t *testing.T) {
	api, cleanup := newTestAPI(t)
	defer cleanup()
	h := api.Routes()

	// Create.
	rec := doRequest(t, h, "POST", "/books", map[string]any{
		"title":  "The Go Book",
		"author": "Grace",
		"year":   2020,
		"isbn":   "111",
	})
	if rec.Code != http.StatusCreated {
		t.Fatalf("create status = %d, body=%s", rec.Code, rec.Body.String())
	}
	var created Book
	if err := json.Unmarshal(rec.Body.Bytes(), &created); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if created.ID == 0 || created.Title != "The Go Book" {
		t.Fatalf("unexpected created book: %+v", created)
	}

	// Get.
	rec = doRequest(t, h, "GET", "/books/1", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("get status = %d, body=%s", rec.Code, rec.Body.String())
	}
	var got Book
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if got.ID != created.ID || got.Title != created.Title {
		t.Fatalf("got = %+v, want %+v", got, created)
	}

	// List with author filter.
	rec = doRequest(t, h, "GET", "/books?author=Grace", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("list status = %d, body=%s", rec.Code, rec.Body.String())
	}
	var listResp struct {
		Books []*Book `json:"books"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &listResp); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if len(listResp.Books) != 1 {
		t.Fatalf("expected 1 book, got %d", len(listResp.Books))
	}

	// List with non-matching filter.
	rec = doRequest(t, h, "GET", "/books?author=Nope", nil)
	if err := json.Unmarshal(rec.Body.Bytes(), &listResp); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if len(listResp.Books) != 0 {
		t.Fatalf("expected 0 books, got %d", len(listResp.Books))
	}

	// Update.
	rec = doRequest(t, h, "PUT", "/books/1", map[string]any{
		"title": "The Go Book (2nd)",
	})
	if rec.Code != http.StatusOK {
		t.Fatalf("update status = %d, body=%s", rec.Code, rec.Body.String())
	}
	var updated Book
	if err := json.Unmarshal(rec.Body.Bytes(), &updated); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if updated.Title != "The Go Book (2nd)" || updated.Author != "Grace" {
		t.Fatalf("updated = %+v", updated)
	}

	// Delete.
	rec = doRequest(t, h, "DELETE", "/books/1", nil)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("delete status = %d, body=%s", rec.Code, rec.Body.String())
	}

	// Get after delete -> 404.
	rec = doRequest(t, h, "GET", "/books/1", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("get-after-delete status = %d, want 404", rec.Code)
	}
}

func TestHealthAndNotFound(t *testing.T) {
	api, cleanup := newTestAPI(t)
	defer cleanup()
	h := api.Routes()

	rec := doRequest(t, h, "GET", "/health", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("health status = %d", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), `"ok"`) {
		t.Fatalf("health body = %s", rec.Body.String())
	}

	// Nonexistent id.
	rec = doRequest(t, h, "GET", "/books/9999", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", rec.Code)
	}

	// Invalid id.
	rec = doRequest(t, h, "GET", "/books/abc", nil)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 for bad id, got %d", rec.Code)
	}
}

func TestServerIntegration(t *testing.T) {
	api, cleanup := newTestAPI(t)
	defer cleanup()

	srv := httptest.NewServer(api.Routes())
	defer srv.Close()
	ctx := context.Background()

	body, _ := json.Marshal(map[string]any{"title": "Net Book", "author": "Bob"})
	req, _ := http.NewRequestWithContext(ctx, http.MethodPost, srv.URL+"/books", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("request: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("status = %d", resp.StatusCode)
	}
}
