package com.example.books;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.sql.SQLException;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class BookRepositoryTest {

    private BookRepository repo;

    @AfterEach
    void tearDown() throws SQLException {
        if (repo != null) repo.close();
    }

    @Test
    void createFindUpdateDeleteWorks() throws SQLException {
        repo = new BookRepository(":memory:");
        Book b = new Book(null, "Title", "Author", 1990, "isbn1");
        Book saved = repo.create(b);
        assertNotNull(saved.getId());
        assertEquals("Title", saved.getTitle());

        Book found = repo.findById(saved.getId());
        assertEquals(saved.getId(), found.getId());
        assertEquals("Author", found.getAuthor());
        assertEquals(1990, found.getYear());

        Book updated = new Book(null, "New", "Author", 2000, "isbn2");
        assertTrue(repo.update(saved.getId(), updated));
        assertEquals("New", repo.findById(saved.getId()).getTitle());

        List<Book> all = repo.findAll(null);
        assertEquals(1, all.size());

        assertTrue(repo.delete(saved.getId()));
        assertNull(repo.findById(saved.getId()));
        assertFalse(repo.delete(saved.getId()));
    }

    @Test
    void authorFilterReturnsOnlyMatchingBooks() throws SQLException {
        repo = new BookRepository(":memory:");
        repo.create(new Book(null, "T1", "Alice", 2000, null));
        repo.create(new Book(null, "T2", "Bob", 2001, null));
        repo.create(new Book(null, "T3", "Alice", 2002, null));

        List<Book> alice = repo.findAll("Alice");
        assertEquals(2, alice.size());
        assertTrue(alice.stream().allMatch(b -> "Alice".equals(b.getAuthor())));

        List<Book> all = repo.findAll(null);
        assertEquals(3, all.size());
    }
}
