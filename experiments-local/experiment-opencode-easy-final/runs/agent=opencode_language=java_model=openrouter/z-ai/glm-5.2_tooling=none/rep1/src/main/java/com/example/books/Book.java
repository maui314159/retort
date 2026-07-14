package com.example.books;

public record Book(
        Long id,
        String title,
        String author,
        Integer year,
        String isbn
) {
    public Book withId(Long newId) {
        return new Book(newId, title, author, year, isbn);
    }
}
