package com.example.books;

import java.util.ArrayList;
import java.util.List;

/**
 * Input validation for incoming {@link Book} payloads.
 *
 * Separated from the controller so it can be unit-tested in isolation
 * and so the rules are documented in one place.
 */
public final class BookInputValidator {

    private BookInputValidator() {
    }

    public static void validateForCreate(Book book) {
        List<String> errors = new ArrayList<>();
        requireText(book == null ? null : book.getTitle(), "title", errors);
        requireText(book == null ? null : book.getAuthor(), "author", errors);
        validateYear(book == null ? null : book.getYear(), errors);
        if (!errors.isEmpty()) {
            throw new ValidationException(String.join("; ", errors));
        }
    }

    public static void validateForUpdate(Book book) {
        // Same rules as create; PUT replaces the resource.
        validateForCreate(book);
    }

    private static void requireText(String value, String field, List<String> errors) {
        if (value == null || value.isBlank()) {
            errors.add(field + " is required");
        }
    }

    private static void validateYear(Integer year, List<String> errors) {
        if (year == null) {
            return; // year is optional
        }
        if (year < 0 || year > 9999) {
            errors.add("year must be between 0 and 9999");
        }
    }
}
