package com.example.bookstore;

import java.util.ArrayList;
import java.util.List;

public final class Validator {
    public static final int MIN_YEAR = 0;
    public static final int MAX_YEAR = 9999;

    private Validator() {}

    public static List<String> validate(Book book) {
        List<String> errors = new ArrayList<>();
        if (book == null) {
            errors.add("body is required");
            return errors;
        }
        if (isBlank(book.getTitle())) {
            errors.add("title is required");
        }
        if (isBlank(book.getAuthor())) {
            errors.add("author is required");
        }
        if (book.getYear() != null && (book.getYear() < MIN_YEAR || book.getYear() > MAX_YEAR)) {
            errors.add("year must be between " + MIN_YEAR + " and " + MAX_YEAR);
        }
        if (book.getIsbn() != null && book.getIsbn().length() > 32) {
            errors.add("isbn must be at most 32 characters");
        }
        return errors;
    }

    private static boolean isBlank(String s) {
        return s == null || s.trim().isEmpty();
    }
}
