package com.example.books.exception;

public class BookNotFoundException extends RuntimeException {
    private final Long id;

    public BookNotFoundException(Long id) {
        super("Book not found with id: " + id);
        this.id = id;
    }

    public Long getId() {
        return id;
    }
}
