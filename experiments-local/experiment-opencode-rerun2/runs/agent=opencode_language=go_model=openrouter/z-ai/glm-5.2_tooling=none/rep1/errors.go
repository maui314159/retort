package main

import "errors"

// Sentinel errors used across the API.
var (
	// ErrNotFound is returned when a book lookup or mutation targets a
	// non-existent ID.
	ErrNotFound = errors.New("book not found")
)
