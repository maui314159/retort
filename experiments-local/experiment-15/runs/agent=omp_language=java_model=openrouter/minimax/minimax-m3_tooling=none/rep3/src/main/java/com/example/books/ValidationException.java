package com.example.books;

/**
 * Thrown when a request fails input validation.
 *
 * Mapped to HTTP 400 by {@link com.example.books.GlobalExceptionHandler}.
 */
public final class ValidationException extends RuntimeException {

    public ValidationException(String message) {
        super(message);
    }
}
