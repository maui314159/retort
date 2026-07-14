package com.example.bookapi.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Positive;

/**
 * Request body for creating or updating a book.
 *
 * @param title  required, non-blank
 * @param author required, non-blank
 * @param year   optional, must be positive when present
 * @param isbn   optional
 */
public record BookRequest(
        @NotBlank(message = "title is required") String title,
        @NotBlank(message = "author is required") String author,
        @Positive(message = "year must be a positive number") Integer year,
        String isbn
) {
}
