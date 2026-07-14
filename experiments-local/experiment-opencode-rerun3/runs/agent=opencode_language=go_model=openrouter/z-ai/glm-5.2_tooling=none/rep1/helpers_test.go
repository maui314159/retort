package main

import (
	"io"
	"strconv"
	"testing"
)

func idStr(id int64) string { return strconv.FormatInt(id, 10) }

func readAll(t *testing.T, r io.Reader) []byte {
	t.Helper()
	b, err := io.ReadAll(r)
	if err != nil {
		t.Fatalf("read body: %v", err)
	}
	return b
}
