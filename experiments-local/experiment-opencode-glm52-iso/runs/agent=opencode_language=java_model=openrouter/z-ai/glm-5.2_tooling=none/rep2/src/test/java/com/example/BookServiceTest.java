package com.example;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.sql.SQLException;

import static org.junit.jupiter.api.Assertions.*;

class BookServiceTest {

    private BookService service;

    @BeforeEach
    void setUp() throws SQLException {
        service = new BookService("jdbc:sqlite::memory:");
    }

    @AfterEach
    void tearDown() throws SQLException {
        service.close();
    }

    @Test
    void createRejectsMissingTitleAndAuthor() throws SQLException {
        ValidationException ex1 = assertThrows(ValidationException.class,
                () -> service.create(new Book(null, null, "Alice", 2000, null)));
        assertEquals("title", ex1.getField());

        ValidationException ex2 = assertThrows(ValidationException.class,
                () -> service.create(new Book(null, "  ", "Alice", 2000, null)));
        assertEquals("title", ex2.getField());

        ValidationException ex3 = assertThrows(ValidationException.class,
                () -> service.create(new Book(null, "Title", "   ", 2000, null)));
        assertEquals("author", ex3.getField());
    }

    @Test
    void createAcceptsAndPersistsValidBook() throws SQLException, ValidationException {
        Book created = service.create(new Book(null, "Dune", "Frank Herbert", 1965, "isbn1"));
        assertNotNull(created.getId());
        Book fetched = service.get(created.getId());
        assertEquals("Dune", fetched.getTitle());
    }

    @Test
    void updateThrowsNotFoundForMissingId() {
        NotFoundException ex = assertThrows(NotFoundException.class,
                () -> service.update(4242L, new Book(null, "T", "A", 2000, null)));
        assertEquals(4242L, ex.getId());
    }

    @Test
    void deleteThrowsNotFoundForMissingId() {
        assertThrows(NotFoundException.class, () -> service.delete(9999L));
    }
}
