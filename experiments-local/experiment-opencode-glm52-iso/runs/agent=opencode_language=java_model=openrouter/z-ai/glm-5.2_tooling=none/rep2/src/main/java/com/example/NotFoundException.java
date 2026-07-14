package com.example;

public class NotFoundException extends Exception {
    private final Long id;

    public NotFoundException(Long id) {
        super("book with id " + id + " not found");
        this.id = id;
    }

    public Long getId() { return id; }
}
