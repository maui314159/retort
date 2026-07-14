package com.example.books;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class BookRepositoryTest {

    private BookRepository repo;

    @BeforeEach
    void setUp() {
        repo = new BookRepository("jdbc:sqlite::memory:");
    }

    @AfterEach
    void tearDown() {
        repo.close();
    }

    @Test
    void createAssignsIdAndRoundtrips() {
        Book created = repo.create(new Book(null, "Dune", "Frank Herbert", 1965, "0441172717"));
        assertNotNull(created.getId());
        assertTrue(created.getId() > 0);

        Optional<Book> loaded = repo.findById(created.getId());
        assertTrue(loaded.isPresent());
        assertEquals(created, loaded.get());
    }

    @Test
    void createAcceptsNullYearAndIsbn() {
        Book created = repo.create(new Book(null, "Anonymous", "Unknown", null, null));
        assertEquals("Anonymous", created.getTitle());
        assertEquals(null, created.getYear());
        assertEquals(null, created.getIsbn());

        Optional<Book> loaded = repo.findById(created.getId());
        assertTrue(loaded.isPresent());
        assertEquals(null, loaded.get().getYear());
    }

    @Test
    void findAllReturnsAllInInsertOrder() {
        repo.create(new Book(null, "A", "Alice", 2000, null));
        repo.create(new Book(null, "B", "Bob", 2001, null));
        repo.create(new Book(null, "C", "Alice", 2002, null));

        List<Book> all = repo.findAll(null);
        assertEquals(3, all.size());
        assertEquals("A", all.get(0).getTitle());
        assertEquals("C", all.get(2).getTitle());
    }

    @Test
    void findAllFiltersByAuthor() {
        repo.create(new Book(null, "A", "Alice", 2000, null));
        repo.create(new Book(null, "B", "Bob", 2001, null));
        repo.create(new Book(null, "C", "Alice", 2002, null));

        List<Book> aliceOnly = repo.findAll("Alice");
        assertEquals(2, aliceOnly.size());
        assertTrue(aliceOnly.stream().allMatch(b -> "Alice".equals(b.getAuthor())));
    }

    @Test
    void findAllTreatsBlankFilterAsNoFilter() {
        repo.create(new Book(null, "A", "Alice", 2000, null));
        repo.create(new Book(null, "B", "Bob", 2001, null));
        assertEquals(2, repo.findAll("   ").size());
    }

    @Test
    void updateChangesFieldsAndReturnsUpdatedRow() {
        Book created = repo.create(new Book(null, "Old", "Alice", 2000, "111"));
        Optional<Book> updated = repo.update(created.getId(),
                new Book(null, "New", "Bob", 2020, "222"));

        assertTrue(updated.isPresent());
        assertEquals("New", updated.get().getTitle());
        assertEquals("Bob", updated.get().getAuthor());
        assertEquals(2020, updated.get().getYear());
        assertEquals("222", updated.get().getIsbn());
        assertEquals(created.getId(), updated.get().getId());
    }

    @Test
    void updateUnknownIdReturnsEmpty() {
        Optional<Book> result = repo.update(9999L, new Book(null, "X", "Y", null, null));
        assertFalse(result.isPresent());
    }

    @Test
    void deleteRemovesRowAndReportsFalseForUnknownId() {
        Book created = repo.create(new Book(null, "A", "Alice", 2000, null));
        assertTrue(repo.delete(created.getId()));
        assertFalse(repo.findById(created.getId()).isPresent());
        assertFalse(repo.delete(9999L));
    }
}
