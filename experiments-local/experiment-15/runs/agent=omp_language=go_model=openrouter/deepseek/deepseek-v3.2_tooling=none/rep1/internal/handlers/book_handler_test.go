package handlers

import (
	"testing"

	"bookapi/internal/models"

	"github.com/stretchr/testify/assert"
)

func TestValidateBook(t *testing.T) {
	tests := []struct {
		name    string
		book    models.Book
		wantErr bool
	}{
		{
			name: "valid book",
			book: models.Book{
				Title:  "Valid Title",
				Author: "Valid Author",
			},
			wantErr: false,
		},
		{
			name: "missing title",
			book: models.Book{
				Author: "Valid Author",
			},
			wantErr: true,
		},
		{
			name: "missing author",
			book: models.Book{
				Title: "Valid Title",
			},
			wantErr: true,
		},
		{
			name: "missing both",
			book: models.Book{},
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := validateBook(&tt.book)
			if tt.wantErr {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)
			}
		})
	}
}

func TestValidationError(t *testing.T) {
	err := &ValidationError{
		Field:   "title",
		Message: "title is required",
	}
	assert.Equal(t, "title is required", err.Error())
}