package com.example.bookstore;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class ValidatorTest {

    @Test
    void rejectsMissingTitleAndAuthor() {
        Book book = new Book(null, null, null, 2020, "isbn");
        List<String> errors = Validator.validate(book);
        assertTrue(errors.contains("title is required"));
        assertTrue(errors.contains("author is required"));
    }

    @Test
    void rejectsBlankTitleAndAuthor() {
        Book book = new Book(null, "   ", "", 2020, null);
        List<String> errors = Validator.validate(book);
        assertTrue(errors.contains("title is required"));
        assertTrue(errors.contains("author is required"));
    }

    @Test
    void acceptsValidBook() {
        Book book = new Book(null, "Dune", "Herbert", 1965, "978-0441172722");
        assertTrue(Validator.validate(book).isEmpty());
    }

    @Test
    void allowsNullYearAndIsbn() {
        Book book = new Book(null, "Title", "Author", null, null);
        assertTrue(Validator.validate(book).isEmpty());
    }

    @Test
    void rejectsOutOfRangeYear() {
        Book book = new Book(null, "T", "A", -1, null);
        assertEquals(1, Validator.validate(book).size());
        Book book2 = new Book(null, "T", "A", 10_000, null);
        assertEquals(1, Validator.validate(book2).size());
    }

    @Test
    void rejectsOverlongIsbn() {
        String longIsbn = "9".repeat(33);
        Book book = new Book(null, "T", "A", 2020, longIsbn);
        List<String> errors = Validator.validate(book);
        assertEquals(1, errors.size());
        assertTrue(errors.get(0).contains("isbn"));
    }

    @Test
    void rejectsNullBody() {
        List<String> errors = Validator.validate(null);
        assertEquals(1, errors.size());
        assertEquals("body is required", errors.get(0));
    }
}
