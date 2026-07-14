package com.example.books.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import org.hibernate.validator.constraints.Length;

public record BookRequest(
        @NotBlank(message = "title is required")
        @Length(max = 500, message = "title must be at most 500 characters")
        String title,

        @NotBlank(message = "author is required")
        @Length(max = 200, message = "author must be at most 200 characters")
        String author,

        Integer year,

        @Length(max = 32, message = "isbn must be at most 32 characters")
        String isbn
) {
    public boolean hasYear() {
        return year != null;
    }
}
