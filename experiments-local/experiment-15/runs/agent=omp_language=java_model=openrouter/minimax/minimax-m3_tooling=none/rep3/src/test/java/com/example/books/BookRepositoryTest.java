package com.example.books;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.SQLException;
import java.util.List;
import java.util.Optional;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * Unit tests for {@link BookRepository}. Each test runs against a
 * private on-disk SQLite file so the embedded engine's per-connection
 * in-memory database does not cause data to disappear between calls.
 */
class BookRepositoryTest {

    private BookRepository repository;
    private Path tmpFile;

    @BeforeEach
    void setUp() throws Exception {
        tmpFile = Files.createTempFile("books-test-", ".db");
        tmpFile.toFile().deleteOnExit();
        Database db = new Database("jdbc:sqlite:" + tmpFile);
        db.initializeSchema();
        repository = new BookRepository(db);
    }

    @Test
    @DisplayName("create assigns a generated id and round-trips all fields")
    void createAssignsIdAndRoundTripsFields() throws SQLException {
        Book book = new Book(null, "Effective Java", "Joshua Bloch", 2008, "978-0134685991");
        Book saved = repository.create(book);

        assertNotNull(saved.getId(), "id should be populated by the database");
        Optional<Book> loaded = repository.findById(saved.getId());
        assertTrue(loaded.isPresent());
        Book got = loaded.get();
        assertEquals("Effective Java", got.getTitle());
        assertEquals("Joshua Bloch", got.getAuthor());
        assertEquals(2008, got.getYear());
        assertEquals("978-0134685991", got.getIsbn());
    }

    @Test
    @DisplayName("create stores null year and isbn as NULL")
    void createStoresNullableFieldsAsNull() throws SQLException {
        Book saved = repository.create(new Book(null, "Untitled", "Anonymous", null, null));
        Book loaded = repository.findById(saved.getId()).orElseThrow();
        assertNull(loaded.getYear());
        assertNull(loaded.getIsbn());
    }

    @Test
    @DisplayName("findAll returns every book when no author filter is supplied")
    void findAllReturnsEverything() throws SQLException {
        repository.create(new Book(null, "A", "Alice", 2000, null));
        repository.create(new Book(null, "B", "Bob", 2001, null));

        List<Book> all = repository.findAll(null);
        assertEquals(2, all.size());
    }

    @Test
    @DisplayName("findAll filters by author case-insensitively")
    void findAllFiltersByAuthor() throws SQLException {
        repository.create(new Book(null, "A1", "Tolkien", 1954, null));
        repository.create(new Book(null, "A2", "tolkien", 1955, null));
        repository.create(new Book(null, "B",  "Rowling", 1997, null));

        List<Book> tolkiens = repository.findAll("TOLKIEN");
        assertEquals(2, tolkiens.size());
        assertTrue(tolkiens.stream().allMatch(b -> b.getAuthor().equalsIgnoreCase("tolkien")));
    }

    @Test
    @DisplayName("update changes fields and leaves other rows untouched")
    void updateChangesFields() throws SQLException {
        Book a = repository.create(new Book(null, "Old", "Author", 1990, "111"));
        Book b = repository.create(new Book(null, "Other", "Author", 2000, "222"));

        Book replacement = new Book(null, "New", "Author", 2024, "999");
        boolean updated = repository.update(a.getId(), replacement);

        assertTrue(updated);
        Book loadedA = repository.findById(a.getId()).orElseThrow();
        assertEquals("New", loadedA.getTitle());
        assertEquals(2024, loadedA.getYear());
        assertEquals("999", loadedA.getIsbn());

        Book loadedB = repository.findById(b.getId()).orElseThrow();
        assertEquals("Other", loadedB.getTitle());
    }

    @Test
    @DisplayName("update returns false when the id does not exist")
    void updateReturnsFalseForUnknownId() throws SQLException {
        boolean updated = repository.update(9999L, new Book(null, "x", "y", null, null));
        assertFalse(updated);
    }

    @Test
    @DisplayName("delete removes a row and reports the outcome")
    void deleteRemovesRow() throws SQLException {
        Book saved = repository.create(new Book(null, "Doomed", "X", null, null));
        assertTrue(repository.delete(saved.getId()));
        assertTrue(repository.findById(saved.getId()).isEmpty());
        assertFalse(repository.delete(saved.getId()), "deleting twice is a no-op");
    }
}
