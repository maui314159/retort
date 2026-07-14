package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strconv"
	"testing"
)

func newTestServer(t *testing.T) (*httptest.Server, *Store) {
	t.Helper()
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "test.db")
	store, err := NewStore(dbPath)
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	t.Cleanup(func() { store.Close(); os.Remove(dbPath) })
	h := NewHandler(store)
	srv := httptest.NewServer(h.Routes())
	t.Cleanup(srv.Close)
	return srv, store
}

func do(t *testing.T, method, url string, body interface{}) (*http.Response, []byte) {
	t.Helper()
	var r *bytes.Reader
	if body != nil {
		b, err := json.Marshal(body)
		if err != nil {
			t.Fatalf("marshal: %v", err)
		}
		r = bytes.NewReader(b)
	} else {
		r = bytes.NewReader(nil)
	}
	req, err := http.NewRequest(method, url, r)
	if err != nil {
		t.Fatalf("new request: %v", err)
	}
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("do: %v", err)
	}
	defer resp.Body.Close()
	var buf bytes.Buffer
	if _, err := buf.ReadFrom(resp.Body); err != nil {
		t.Fatalf("read body: %v", err)
	}
	return resp, buf.Bytes()
}

func TestHealth(t *testing.T) {
	srv, _ := newTestServer(t)
	resp, b := do(t, http.MethodGet, srv.URL+"/health", nil)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("status = %d, want 200, body=%s", resp.StatusCode, b)
	}
	var m map[string]string
	if err := json.Unmarshal(b, &m); err != nil {
		t.Fatalf("unmarshal: %v body=%s", err, b)
	}
	if m["status"] != "ok" {
		t.Fatalf("status=%q want ok", m["status"])
	}
}

func TestCreateListGetUpdateDelete(t *testing.T) {
	srv, _ := newTestServer(t)

	// Validation: missing title/author
	resp, _ := do(t, http.MethodPost, srv.URL+"/books", Book{Author: "A"})
	if resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("bad book got %d want 400", resp.StatusCode)
	}

	// Create
	resp, b := do(t, http.MethodPost, srv.URL+"/books", Book{Title: "T1", Author: "Alice", Year: 2001, ISBN: "i1"})
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("create status %d want 201 body=%s", resp.StatusCode, b)
	}
	var created Book
	if err := json.Unmarshal(b, &created); err != nil {
		t.Fatalf("unmarshal created: %v", err)
	}
	if created.ID == 0 || created.Title != "T1" {
		t.Fatalf("unexpected created book: %+v", created)
	}

	// Get
	resp, b = do(t, http.MethodGet, srv.URL+"/books/"+itoa(created.ID), nil)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("get status %d want 200 body=%s", resp.StatusCode, b)
	}
	var got Book
	if err := json.Unmarshal(b, &got); err != nil {
		t.Fatalf("unmarshal get: %v", err)
	}
	if got.Title != "T1" || got.Author != "Alice" {
		t.Fatalf("unexpected get book: %+v", got)
	}

	// Get nonexistent
	resp, _ = do(t, http.MethodGet, srv.URL+"/books/9999", nil)
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("missing get status %d want 404", resp.StatusCode)
	}

	// Create second book by different author
	resp, _ = do(t, http.MethodPost, srv.URL+"/books", Book{Title: "T2", Author: "Bob"})
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("second create status %d", resp.StatusCode)
	}

	// List all
	resp, b = do(t, http.MethodGet, srv.URL+"/books", nil)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("list status %d body=%s", resp.StatusCode, b)
	}
	var all []Book
	if err := json.Unmarshal(b, &all); err != nil {
		t.Fatalf("unmarshal list: %v", err)
	}
	if len(all) != 2 {
		t.Fatalf("len(all)=%d want 2", len(all))
	}

	// List filter by author
	resp, b = do(t, http.MethodGet, srv.URL+"/books?author=Alice", nil)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("filter status %d body=%s", resp.StatusCode, b)
	}
	var filtered []Book
	if err := json.Unmarshal(b, &filtered); err != nil {
		t.Fatalf("unmarshal filter: %v", err)
	}
	if len(filtered) != 1 || filtered[0].Author != "Alice" {
		t.Fatalf("filtered=%+v want 1 Alice", filtered)
	}

	// Update
	resp, b = do(t, http.MethodPut, srv.URL+"/books/"+itoa(created.ID), Book{Title: "T1-updated", Author: "Alice", Year: 2002})
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("update status %d body=%s", resp.StatusCode, b)
	}
	var updated Book
	if err := json.Unmarshal(b, &updated); err != nil {
		t.Fatalf("unmarshal updated: %v", err)
	}
	if updated.Title != "T1-updated" || updated.Year != 2002 {
		t.Fatalf("unexpected updated: %+v", updated)
	}

	// Update nonexistent
	resp, _ = do(t, http.MethodPut, srv.URL+"/books/9999", Book{Title: "X", Author: "Y"})
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("update missing status %d want 404", resp.StatusCode)
	}

	// Delete
	resp, _ = do(t, http.MethodDelete, srv.URL+"/books/"+itoa(created.ID), nil)
	if resp.StatusCode != http.StatusNoContent {
		t.Fatalf("delete status %d want 204", resp.StatusCode)
	}

	// Delete again -> 404
	resp, _ = do(t, http.MethodDelete, srv.URL+"/books/"+itoa(created.ID), nil)
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("re-delete status %d want 404", resp.StatusCode)
	}
}

func TestInvalidJSON(t *testing.T) {
	srv, _ := newTestServer(t)
	req, _ := http.NewRequest(http.MethodPost, srv.URL+"/books", bytes.NewReader([]byte("{not json")))
	req.Header.Set("Content-Type", "application/json")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("status %d want 400", resp.StatusCode)
	}
}

func itoa(id int64) string {
	return strconv.FormatInt(id, 10)
}
