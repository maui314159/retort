package books

import (
	"bytes"
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// newTestServer builds a Server backed by an in-memory store and
// returns the http.Handler plus a helper for issuing JSON requests.
func newTestServer(t *testing.T) http.Handler {
	t.Helper()
	store, err := Open(":memory:")
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	t.Cleanup(func() { _ = store.Close() })
	// Discard log output during tests.
	return NewServer(store, slog.New(slog.NewTextHandler(io.Discard, nil))).Routes()
}

// doJSON issues req against h and returns the recorded response.
func doJSON(t *testing.T, h http.Handler, method, path string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var rdr io.Reader
	if body != nil {
		buf, err := json.Marshal(body)
		if err != nil {
			t.Fatalf("marshal body: %v", err)
		}
		rdr = bytes.NewReader(buf)
	}
	req := httptest.NewRequest(method, path, rdr)
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)
	return rr
}

// decodeBody unmarshals rr.Body into v, failing the test on error.
func decodeBody(t *testing.T, rr *httptest.ResponseRecorder, v any) {
	t.Helper()
	if err := json.Unmarshal(rr.Body.Bytes(), v); err != nil {
		t.Fatalf("unmarshal %q: %v", rr.Body.String(), err)
	}
}

// TestHealth is a one-line sanity check that the health endpoint is
// reachable and returns the documented payload.
func TestHealth(t *testing.T) {
	rr := doJSON(t, newTestServer(t), http.MethodGet, "/health", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("status: got %d, want 200", rr.Code)
	}
	if ct := rr.Header().Get("Content-Type"); !strings.HasPrefix(ct, "application/json") {
		t.Errorf("Content-Type: got %q, want application/json...", ct)
	}
	var body map[string]string
	decodeBody(t, rr, &body)
	if body["status"] != "ok" {
		t.Errorf("status field: got %q, want %q", body["status"], "ok")
	}
}

// TestCreateAndGet covers the POST → GET happy path: create a book,
// then fetch it back and assert the wire format matches the input.
func TestCreateAndGet(t *testing.T) {
	h := newTestServer(t)

	create := doJSON(t, h, http.MethodPost, "/books", Book{
		Title:  "Crafting Interpreters",
		Author: "Robert Nystrom",
		Year:   2021,
		ISBN:   "978-0990582939",
	})
	if create.Code != http.StatusCreated {
		t.Fatalf("POST status: got %d (%s), want 201", create.Code, create.Body.String())
	}
	var created Book
	decodeBody(t, create, &created)
	if created.ID == 0 {
		t.Fatal("POST response missing id")
	}
	if created.Title != "Crafting Interpreters" {
		t.Errorf("Title: got %q, want %q", created.Title, "Crafting Interpreters")
	}

	get := doJSON(t, h, http.MethodGet, "/books/"+itoa(created.ID), nil)
	if get.Code != http.StatusOK {
		t.Fatalf("GET status: got %d, want 200", get.Code)
	}
	var fetched Book
	decodeBody(t, get, &fetched)
	if fetched != created {
		t.Errorf("GET roundtrip: got %+v, want %+v", fetched, created)
	}
}

// TestListFilter seeds several books and verifies List + ?author= filter.
func TestListFilter(t *testing.T) {
	h := newTestServer(t)

	for _, b := range []Book{
		{Title: "B1", Author: "Alice"},
		{Title: "B2", Author: "Bob"},
		{Title: "B3", Author: "Alice"},
	} {
		if rr := doJSON(t, h, http.MethodPost, "/books", b); rr.Code != http.StatusCreated {
			t.Fatalf("seed POST %+v: status %d, body %s", b, rr.Code, rr.Body.String())
		}
	}

	// Unfiltered list should be 3 books.
	rr := doJSON(t, h, http.MethodGet, "/books", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("GET /books: status %d", rr.Code)
	}
	var all []Book
	decodeBody(t, rr, &all)
	if len(all) != 3 {
		t.Errorf("GET /books: got %d, want 3", len(all))
	}

	// Filtered list should be 2 books by Alice.
	rr = doJSON(t, h, http.MethodGet, "/books?author=Alice", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("GET /books?author=Alice: status %d", rr.Code)
	}
	var alice []Book
	decodeBody(t, rr, &alice)
	if len(alice) != 2 {
		t.Fatalf("GET /books?author=Alice: got %d, want 2", len(alice))
	}
	for _, b := range alice {
		if b.Author != "Alice" {
			t.Errorf("filter leak: got author %q", b.Author)
		}
	}

	// Empty result must be an empty JSON array, never `null`.
	rr = doJSON(t, h, http.MethodGet, "/books?author=Carol", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("GET /books?author=Carol: status %d", rr.Code)
	}
	if got := strings.TrimSpace(rr.Body.String()); got != "[]" {
		t.Errorf("empty filter: body = %q, want %q", got, "[]")
	}
}

// TestUpdateAndDelete verifies PUT persists changes and DELETE returns
// 204 and makes subsequent GETs return 404.
func TestUpdateAndDelete(t *testing.T) {
	h := newTestServer(t)

	rr := doJSON(t, h, http.MethodPost, "/books", Book{Title: "Old", Author: "A", Year: 2000})
	if rr.Code != http.StatusCreated {
		t.Fatalf("seed: status %d", rr.Code)
	}
	var b Book
	decodeBody(t, rr, &b)

	upd := doJSON(t, h, http.MethodPut, "/books/"+itoa(b.ID), Book{Title: "New", Author: "A", Year: 2024, ISBN: "X"})
	if upd.Code != http.StatusOK {
		t.Fatalf("PUT status: got %d (%s), want 200", upd.Code, upd.Body.String())
	}
	var updated Book
	decodeBody(t, upd, &updated)
	if updated.Title != "New" || updated.Year != 2024 {
		t.Errorf("PUT response: %+v", updated)
	}

	rr = doJSON(t, h, http.MethodGet, "/books/"+itoa(b.ID), nil)
	var fetched Book
	decodeBody(t, rr, &fetched)
	if fetched.Title != "New" {
		t.Errorf("PUT did not persist: %+v", fetched)
	}

	del := doJSON(t, h, http.MethodDelete, "/books/"+itoa(b.ID), nil)
	if del.Code != http.StatusNoContent {
		t.Fatalf("DELETE status: got %d, want 204", del.Code)
	}
	if del.Body.Len() != 0 {
		t.Errorf("DELETE body should be empty, got %q", del.Body.String())
	}

	miss := doJSON(t, h, http.MethodGet, "/books/"+itoa(b.ID), nil)
	if miss.Code != http.StatusNotFound {
		t.Errorf("GET after DELETE: got %d, want 404", miss.Code)
	}
}

// TestValidationErrors covers the two "required field" rejection paths
// (missing title, missing author) plus a malformed-JSON case.
func TestValidationErrors(t *testing.T) {
	h := newTestServer(t)

	cases := []struct {
		name string
		body any
		want string
	}{
		{"missing title", Book{Author: "A"}, "title is required"},
		{"empty title", Book{Title: "", Author: "A"}, "title is required"},
		{"missing author", Book{Title: "T"}, "author is required"},
		{"empty author", Book{Title: "T", Author: ""}, "author is required"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			rr := doJSON(t, h, http.MethodPost, "/books", tc.body)
			if rr.Code != http.StatusBadRequest {
				t.Fatalf("status: got %d, want 400", rr.Code)
			}
			var body map[string]string
			decodeBody(t, rr, &body)
			if body["error"] != tc.want {
				t.Errorf("error: got %q, want %q", body["error"], tc.want)
			}
		})
	}

	// Malformed JSON should also 400 with a clear message.
	req := httptest.NewRequest(http.MethodPost, "/books", strings.NewReader("{not json"))
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)
	if rr.Code != http.StatusBadRequest {
		t.Errorf("malformed JSON: got %d, want 400", rr.Code)
	}
	if !strings.Contains(rr.Body.String(), "invalid JSON") {
		t.Errorf("malformed JSON body: %q", rr.Body.String())
	}
}

// TestNotFoundAndBadID confirms 404 vs 400 behavior for the {id} routes.
func TestNotFoundAndBadID(t *testing.T) {
	h := newTestServer(t)

	rr := doJSON(t, h, http.MethodGet, "/books/12345", nil)
	if rr.Code != http.StatusNotFound {
		t.Errorf("missing GET: got %d, want 404", rr.Code)
	}

	rr = doJSON(t, h, http.MethodGet, "/books/not-a-number", nil)
	if rr.Code != http.StatusBadRequest {
		t.Errorf("non-numeric id: got %d, want 400", rr.Code)
	}

	rr = doJSON(t, h, http.MethodDelete, "/books/12345", nil)
	if rr.Code != http.StatusNotFound {
		t.Errorf("missing DELETE: got %d, want 404", rr.Code)
	}

	rr = doJSON(t, h, http.MethodPut, "/books/12345", Book{Title: "T", Author: "A"})
	if rr.Code != http.StatusNotFound {
		t.Errorf("missing PUT: got %d, want 404", rr.Code)
	}
}

// itoa is a tiny int64-to-string helper that avoids pulling strconv
// into the test files just for one call site.
func itoa(n int64) string {
	if n == 0 {
		return "0"
	}
	neg := n < 0
	if neg {
		n = -n
	}
	var buf [20]byte
	i := len(buf)
	for n > 0 {
		i--
		buf[i] = byte('0' + n%10)
		n /= 10
	}
	if neg {
		i--
		buf[i] = '-'
	}
	return string(buf[i:])
}
