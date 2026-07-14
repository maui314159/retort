package com.example.bookapi.exception;

/**
 * Thrown when a book lookup/update/delete targets a non-existent id.
 */
public class BookNotFoundException extends RuntimeException {

    public BookNotFoundException(Long id) {
        super("Book not found: " + id);
    }
}
