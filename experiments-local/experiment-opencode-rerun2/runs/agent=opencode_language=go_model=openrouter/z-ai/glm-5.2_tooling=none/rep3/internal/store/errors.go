package store

import "errors"

// ErrNotFound is returned when no row matches the requested id.
var ErrNotFound = errors.New("book not found")
