package api_test

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"

	"books/internal/api"
	"books/internal/book"
	"books/internal/store"
)

// newTestServer wires an API backed by a fresh in-memory-ish SQLite file and
// returns the http.Handler plus a cleanup. The cleanup closes the store.
func newTestServer(t *testing.T) (http.Handler, *store.Store) {
	t.Helper()
	dir := t.TempDir()
	s, err := store.Open(filepath.Join(dir, "test.db"))
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	t.Cleanup(func() { _ = s.Close() })

	a := &api.API{Store: s, Logger: log.New(io.Discard, "", 0)}
	return a.Handler(), s
}

// do executes a request against the handler and returns the response. It
// also enforces Content-Type and JSON-decodes the body when requested.
func do(t *testing.T, h http.Handler, method, target string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var rdr io.Reader
	if body != nil {
		buf, err := json.Marshal(body)
		if err != nil {
			t.Fatalf("marshal body: %v", err)
		}
		rdr = bytes.NewReader(buf)
	}
	req := httptest.NewRequest(method, target, rdr)
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)
	return rr
}

func decode[T any](t *testing.T, rr *httptest.ResponseRecorder) T {
	t.Helper()
	var v T
	if err := json.Unmarshal(rr.Body.Bytes(), &v); err != nil {
		t.Fatalf("decode response: %v (body=%q)", err, rr.Body.String())
	}
	return v
}

// ---------- /health ----------

func TestHealth(t *testing.T) {
	t.Parallel()
	h, _ := newTestServer(t)
	rr := do(t, h, http.MethodGet, "/health", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("status: got %d, want 200", rr.Code)
	}
	if ct := rr.Header().Get("Content-Type"); !strings.HasPrefix(ct, "application/json") {
		t.Fatalf("content-type: got %q", ct)
	}
	body := decode[map[string]string](t, rr)
	if body["status"] != "ok" {
		t.Fatalf("health body: %+v", body)
	}
}

// ---------- POST /books ----------

func TestCreateBook(t *testing.T) {
	t.Parallel()
	h, _ := newTestServer(t)
	in := book.Input{Title: "The Mythical Man-Month", Author: "Fred Brooks", Year: 1975, ISBN: "0201835959"}
	rr := do(t, h, http.MethodPost, "/books", in)
	if rr.Code != http.StatusCreated {
		t.Fatalf("status: got %d body=%q", rr.Code, rr.Body.String())
	}
	got := decode[book.Book](t, rr)
	if got.ID <= 0 {
		t.Fatalf("expected positive ID, got %d", got.ID)
	}
	if got.Title != in.Title || got.Author != in.Author || got.Year != in.Year || got.ISBN != in.ISBN {
		t.Fatalf("round-trip mismatch: %+v", got)
	}
	// The Location header is a nice-to-have for a REST create; if we set it
	// (and we should), check it.
	if loc := rr.Header().Get("Location"); loc != "" {
		want := "/books/" + itoa(got.ID)
		if loc != want {
			t.Fatalf("Location: got %q, want %q", loc, want)
		}
	}
}

func TestCreateBookValidation(t *testing.T) {
	t.Parallel()
	h, _ := newTestServer(t)

	cases := []struct {
		name string
		body any
	}{
		{"missing title", book.Input{Author: "A"}},
		{"missing author", book.Input{Title: "T"}},
		{"whitespace title", book.Input{Title: "   ", Author: "A"}},
		{"whitespace author", book.Input{Title: "T", Author: "  \t "}},
		{"negative year", book.Input{Title: "T", Author: "A", Year: -1}},
	}
	for _, tc := range cases {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			rr := do(t, h, http.MethodPost, "/books", tc.body)
			if rr.Code != http.StatusBadRequest {
				t.Fatalf("status: got %d body=%q", rr.Code, rr.Body.String())
			}
		})
	}
}

func TestCreateBookMalformedJSON(t *testing.T) {
	t.Parallel()
	h, _ := newTestServer(t)
	req := httptest.NewRequest(http.MethodPost, "/books", strings.NewReader(`{"title":`))
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)
	if rr.Code != http.StatusBadRequest {
		t.Fatalf("status: got %d, want 400", rr.Code)
	}
}

func TestCreateBookUnknownField(t *testing.T) {
	t.Parallel()
	h, _ := newTestServer(t)
	// DisallowUnknownFields should reject extra keys so clients don't think
	// their typo'd field was applied.
	req := httptest.NewRequest(http.MethodPost, "/books", strings.NewReader(`{"title":"T","author":"A","bogus":1}`))
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)
	if rr.Code != http.StatusBadRequest {
		t.Fatalf("status: got %d, want 400", rr.Code)
	}
}

// ---------- GET /books ----------

func TestListBooks(t *testing.T) {
	t.Parallel()
	h, s := newTestServer(t)
	ctx := context.Background()

	// Empty list returns [] not null.
	rr := do(t, h, http.MethodGet, "/books", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("status: got %d", rr.Code)
	}
	body := decode[[]book.Book](t, rr)
	if body == nil {
		t.Fatalf("expected empty array, got null")
	}

	// Seed two books and list them.
	for _, in := range []book.Input{
		{Title: "T1", Author: "Fowler", Year: 1999},
		{Title: "T2", Author: "Go Team", Year: 2020},
	} {
		if _, err := s.Create(ctx, in); err != nil {
			t.Fatalf("seed: %v", err)
		}
	}

	rr = do(t, h, http.MethodGet, "/books", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("status: got %d", rr.Code)
	}
	all := decode[[]book.Book](t, rr)
	if len(all) != 2 {
		t.Fatalf("list: got %d, want 2", len(all))
	}

	rr = do(t, h, http.MethodGet, "/books?author=fowler", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("status filter: got %d", rr.Code)
	}
	filtered := decode[[]book.Book](t, rr)
	if len(filtered) != 1 || filtered[0].Author != "Fowler" {
		t.Fatalf("filtered: %+v", filtered)
	}
}

// ---------- GET /books/{id} ----------

func TestGetBook(t *testing.T) {
	t.Parallel()
	h, s := newTestServer(t)
	ctx := context.Background()

	created, err := s.Create(ctx, book.Input{Title: "T", Author: "A", Year: 2000})
	if err != nil {
		t.Fatalf("create: %v", err)
	}

	rr := do(t, h, http.MethodGet, "/books/"+itoa(created.ID), nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("status: got %d", rr.Code)
	}
	got := decode[book.Book](t, rr)
	if got.ID != created.ID {
		t.Fatalf("get: got %+v, want ID %d", got, created.ID)
	}
}

func TestGetBookNotFound(t *testing.T) {
	t.Parallel()
	h, _ := newTestServer(t)
	rr := do(t, h, http.MethodGet, "/books/9999", nil)
	if rr.Code != http.StatusNotFound {
		t.Fatalf("status: got %d, want 404", rr.Code)
	}
}

func TestGetBookInvalidID(t *testing.T) {
	t.Parallel()
	h, _ := newTestServer(t)
	rr := do(t, h, http.MethodGet, "/books/notanumber", nil)
	if rr.Code != http.StatusBadRequest {
		t.Fatalf("status: got %d, want 400", rr.Code)
	}
}

// ---------- PUT /books/{id} ----------

func TestUpdateBook(t *testing.T) {
	t.Parallel()
	h, s := newTestServer(t)
	ctx := context.Background()
	created, err := s.Create(ctx, book.Input{Title: "Old", Author: "A", Year: 2000})
	if err != nil {
		t.Fatalf("create: %v", err)
	}

	rr := do(t, h, http.MethodPut, "/books/"+itoa(created.ID), book.Input{Title: "New", Author: "A", Year: 2001})
	if rr.Code != http.StatusOK {
		t.Fatalf("status: got %d body=%q", rr.Code, rr.Body.String())
	}
	got := decode[book.Book](t, rr)
	if got.Title != "New" || got.Year != 2001 {
		t.Fatalf("update did not apply: %+v", got)
	}
}

func TestUpdateBookValidation(t *testing.T) {
	t.Parallel()
	h, s := newTestServer(t)
	ctx := context.Background()
	created, err := s.Create(ctx, book.Input{Title: "T", Author: "A"})
	if err != nil {
		t.Fatalf("create: %v", err)
	}
	rr := do(t, h, http.MethodPut, "/books/"+itoa(created.ID), book.Input{Title: "", Author: "A"})
	if rr.Code != http.StatusBadRequest {
		t.Fatalf("status: got %d, want 400", rr.Code)
	}
}

func TestUpdateBookNotFound(t *testing.T) {
	t.Parallel()
	h, _ := newTestServer(t)
	rr := do(t, h, http.MethodPut, "/books/9999", book.Input{Title: "T", Author: "A"})
	if rr.Code != http.StatusNotFound {
		t.Fatalf("status: got %d, want 404", rr.Code)
	}
}

// ---------- DELETE /books/{id} ----------

func TestDeleteBook(t *testing.T) {
	t.Parallel()
	h, s := newTestServer(t)
	ctx := context.Background()
	created, err := s.Create(ctx, book.Input{Title: "T", Author: "A"})
	if err != nil {
		t.Fatalf("create: %v", err)
	}

	rr := do(t, h, http.MethodDelete, "/books/"+itoa(created.ID), nil)
	if rr.Code != http.StatusNoContent {
		t.Fatalf("status: got %d, want 204 body=%q", rr.Code, rr.Body.String())
	}
	// 204 means no body — assert that.
	if rr.Body.Len() != 0 {
		t.Fatalf("expected empty body, got %q", rr.Body.String())
	}

	// Subsequent get is a 404.
	rr = do(t, h, http.MethodGet, "/books/"+itoa(created.ID), nil)
	if rr.Code != http.StatusNotFound {
		t.Fatalf("post-delete get: got %d, want 404", rr.Code)
	}
}

func TestDeleteBookNotFound(t *testing.T) {
	t.Parallel()
	h, _ := newTestServer(t)
	rr := do(t, h, http.MethodDelete, "/books/9999", nil)
	if rr.Code != http.StatusNotFound {
		t.Fatalf("status: got %d, want 404", rr.Code)
	}
}

// ---------- routing ----------

func TestMethodNotAllowed(t *testing.T) {
	t.Parallel()
	h, _ := newTestServer(t)
	// PATCH is not registered anywhere — Go 1.22 mux returns 405 for
	// patterns that match the path but not the method.
	rr := do(t, h, http.MethodPatch, "/books", nil)
	if rr.Code != http.StatusMethodNotAllowed {
		t.Fatalf("status: got %d, want 405", rr.Code)
	}
}

func TestNotFound(t *testing.T) {
	t.Parallel()
	h, _ := newTestServer(t)
	rr := do(t, h, http.MethodGet, "/nope", nil)
	if rr.Code != http.StatusNotFound {
		t.Fatalf("status: got %d, want 404", rr.Code)
	}
}

// itoa is a tiny stdlib-free formatter used to keep the test file's imports
// minimal. strconv would work too, but this avoids dragging in a name for
// the handful of uses here.
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
