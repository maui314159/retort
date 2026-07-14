package handlers_test

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"

	"bookapi/internal/handlers"
	"bookapi/internal/models"
	"bookapi/internal/store"
)

func newTestServer(t *testing.T) (*httptest.Server, *store.Store) {
	t.Helper()
	s, err := store.Open(":memory:")
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	t.Cleanup(func() { _ = s.Close() })
	h := handlers.New(s)
	srv := httptest.NewServer(h.Routes())
	t.Cleanup(srv.Close)
	return srv, s
}

func do(t *testing.T, srv *httptest.Server, method, path string, body interface{}) *httptest.ResponseRecorder {
	t.Helper()
	var r *http.Request
	if body != nil {
		buf, _ := json.Marshal(body)
		r = httptest.NewRequest(method, path, bytes.NewReader(buf))
		r.Header.Set("Content-Type", "application/json")
	} else {
		r = httptest.NewRequest(method, path, nil)
	}
	rr := httptest.NewRecorder()
	srv.Config.Handler.ServeHTTP(rr, r)
	return rr
}

func TestCreateBookValidation(t *testing.T) {
	srv, _ := newTestServer(t)

	// Missing required fields -> 400 with validation error body.
	rr := do(t, srv, "POST", "/books", map[string]string{"title": ""})
	if rr.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d: %s", rr.Code, rr.Body.String())
	}
	var ve models.ValidationError
	if err := json.Unmarshal(rr.Body.Bytes(), &ve); err != nil {
		t.Fatal(err)
	}
	if ve.Field != "title" {
		t.Fatalf("expected field=title, got %q", ve.Field)
	}

	// Missing author.
	rr = do(t, srv, "POST", "/books", map[string]string{"title": "T"})
	if rr.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 for missing author, got %d", rr.Code)
	}
	if err := json.Unmarshal(rr.Body.Bytes(), &ve); err != nil {
		t.Fatal(err)
	}
	if ve.Field != "author" {
		t.Fatalf("expected field=author, got %q", ve.Field)
	}
}

func TestCreateListGetUpdateDeleteFlow(t *testing.T) {
	srv, _ := newTestServer(t)

	// Create
	rr := do(t, srv, "POST", "/books", models.BookInput{
		Title: "The Pragmatic Programmer", Author: "Hunt", Year: 1999, ISBN: "978-0201616224",
	})
	if rr.Code != http.StatusCreated {
		t.Fatalf("create: expected 201, got %d: %s", rr.Code, rr.Body.String())
	}
	var created models.Book
	if err := json.Unmarshal(rr.Body.Bytes(), &created); err != nil {
		t.Fatal(err)
	}
	if created.ID == 0 {
		t.Fatal("expected non-zero id")
	}

	idStr := strconv.FormatInt(created.ID, 10)

	// Get
	rr = do(t, srv, "GET", "/books/"+idStr, nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("get: expected 200, got %d", rr.Code)
	}

	// List all
	rr = do(t, srv, "GET", "/books", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("list: expected 200, got %d", rr.Code)
	}
	var list []models.Book
	if err := json.Unmarshal(rr.Body.Bytes(), &list); err != nil {
		t.Fatal(err)
	}
	if len(list) != 1 {
		t.Fatalf("expected 1 book, got %d", len(list))
	}

	// List with author filter match
	rr = do(t, srv, "GET", "/books?author=Hunt", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("list filter: expected 200, got %d", rr.Code)
	}
	if err := json.Unmarshal(rr.Body.Bytes(), &list); err != nil {
		t.Fatal(err)
	}
	if len(list) != 1 {
		t.Fatalf("expected 1 book for author=Hunt, got %d", len(list))
	}

	// List with author filter no match returns []
	rr = do(t, srv, "GET", "/books?author=Nobody", nil)
	if err := json.Unmarshal(rr.Body.Bytes(), &list); err != nil {
		t.Fatal(err)
	}
	if len(list) != 0 {
		t.Fatalf("expected 0 books, got %d", len(list))
	}

	// Update
	rr = do(t, srv, "PUT", "/books/"+idStr, models.BookInput{
		Title: "Pragmatic Programmer, The", Author: "Hunt & Thomas", Year: 1999, ISBN: "978-0201616224",
	})
	if rr.Code != http.StatusOK {
		t.Fatalf("update: expected 200, got %d: %s", rr.Code, rr.Body.String())
	}
	var updated models.Book
	if err := json.Unmarshal(rr.Body.Bytes(), &updated); err != nil {
		t.Fatal(err)
	}
	if updated.Author != "Hunt & Thomas" {
		t.Fatalf("update did not apply, got %+v", updated)
	}

	// Delete
	rr = do(t, srv, "DELETE", "/books/"+idStr, nil)
	if rr.Code != http.StatusNoContent {
		t.Fatalf("delete: expected 204, got %d", rr.Code)
	}
	// Subsequent GET -> 404
	rr = do(t, srv, "GET", "/books/"+idStr, nil)
	if rr.Code != http.StatusNotFound {
		t.Fatalf("get after delete: expected 404, got %d", rr.Code)
	}
}

func TestGetInvalidID(t *testing.T) {
	srv, _ := newTestServer(t)
	rr := do(t, srv, "GET", "/books/abc", nil)
	if rr.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 for non-numeric id, got %d", rr.Code)
	}
}

func TestHealth(t *testing.T) {
	srv, _ := newTestServer(t)
	rr := do(t, srv, "GET", "/health", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rr.Code)
	}
	var body map[string]string
	if err := json.Unmarshal(rr.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if body["status"] != "ok" {
		t.Fatalf("expected status=ok, got %v", body)
	}
}


