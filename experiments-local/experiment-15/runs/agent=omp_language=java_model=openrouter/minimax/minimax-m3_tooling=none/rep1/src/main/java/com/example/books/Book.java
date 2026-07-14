package com.example.books;

import java.util.Objects;

/**
 * Immutable representation of a book. Use {@link #toBuilder()} to derive an
 * updated copy for PUT requests. The {@code id} is assigned by the repository
 * on insert; it is null in client-supplied input.
 */
public final class Book {

    private final Long id;
    private final String title;
    private final String author;
    private final Integer year;
    private final String isbn;

    public Book(Long id, String title, String author, Integer year, String isbn) {
        this.id = id;
        this.title = title;
        this.author = author;
        this.year = year;
        this.isbn = isbn;
    }

    public Long getId() {
        return id;
    }

    public String getTitle() {
        return title;
    }

    public String getAuthor() {
        return author;
    }

    public Integer getYear() {
        return year;
    }

    public String getIsbn() {
        return isbn;
    }

    public Book withId(long newId) {
        return new Book(newId, title, author, year, isbn);
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof Book other)) return false;
        return Objects.equals(id, other.id)
                && Objects.equals(title, other.title)
                && Objects.equals(author, other.author)
                && Objects.equals(year, other.year)
                && Objects.equals(isbn, other.isbn);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, title, author, year, isbn);
    }

    @Override
    public String toString() {
        return "Book{id=" + id + ", title='" + title + "', author='" + author
                + "', year=" + year + ", isbn='" + isbn + "'}";
    }
}
