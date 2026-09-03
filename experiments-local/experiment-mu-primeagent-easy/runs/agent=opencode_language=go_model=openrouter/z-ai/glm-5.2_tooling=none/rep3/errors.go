package main

import "errors"

// ErrNotFound is returned when a book does not exist.
var ErrNotFound = errors.New("book not found")
