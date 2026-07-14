package com.example.books;

/**
 * Thrown when a referenced resource does not exist.
 *
 * Mapped to HTTP 404 by {@link com.example.books.GlobalExceptionHandler}.
 */
public final class NotFoundException extends RuntimeException {

    public NotFoundException(String message) {
        super(message);
    }
}
