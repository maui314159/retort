package main

import "errors"

var ErrNotFound = errors.New("book not found")

type ValidationError struct {
	Fields map[string]string
}

func (e *ValidationError) Error() string {
	msg := "validation error"
	for k, v := range e.Fields {
		msg += "; " + k + ": " + v
	}
	return msg
}

func validateBook(in bookInput) (*Book, error) {
	verr := &ValidationError{Fields: map[string]string{}}
	b := &Book{}

	if in.Title == nil || *in.Title == "" {
		verr.Fields["title"] = "title is required"
	} else {
		b.Title = *in.Title
	}

	if in.Author == nil || *in.Author == "" {
		verr.Fields["author"] = "author is required"
	} else {
		b.Author = *in.Author
	}

	if in.Year != nil {
		b.Year = *in.Year
	}
	if in.ISBN != nil {
		b.ISBN = *in.ISBN
	}

	if len(verr.Fields) > 0 {
		return nil, verr
	}
	return b, nil
}

func validatePartial(in bookInput) (*Book, error) {
	verr := &ValidationError{Fields: map[string]string{}}
	b := &Book{}

	if in.Title == nil || *in.Title == "" {
		verr.Fields["title"] = "title is required"
	} else {
		b.Title = *in.Title
	}
	if in.Author == nil || *in.Author == "" {
		verr.Fields["author"] = "author is required"
	} else {
		b.Author = *in.Author
	}
	if in.Year != nil {
		b.Year = *in.Year
	}
	if in.ISBN != nil {
		b.ISBN = *in.ISBN
	}

	if len(verr.Fields) > 0 {
		return nil, verr
	}
	return b, nil
}
