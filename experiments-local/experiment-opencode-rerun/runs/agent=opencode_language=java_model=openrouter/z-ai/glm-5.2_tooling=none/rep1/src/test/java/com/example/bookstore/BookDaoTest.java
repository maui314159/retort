package com.example.bookstore;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.sql.SQLException;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;

class BookDaoTest {

    private BookDao dao;

    @BeforeEach
    void setUp() throws SQLException {
        dao = new BookDao("jdbc:sqlite::memory:");
        dao.init();
    }

    @Test
    void createAssignsIdAndPersists() throws SQLException {
        Book book = new Book(null, "The Pragmatic Programmer", "Hunt & Thomas", 1999, "978-0201616224");
        Book saved = dao.create(book);

        assertNotNull(saved.getId(), "generated id should be set");
        assertTrue(saved.getId() > 0);

        Optional<Book> fetched = dao.get(saved.getId());
        assertTrue(fetched.isPresent());
        assertEquals("The Pragmatic Programmer", fetched.get().getTitle());
        assertEquals("Hunt & Thomas", fetched.get().getAuthor());
        assertEquals(1999, fetched.get().getYear());
        assertEquals("978-0201616224", fetched.get().getIsbn());
    }

    @Test
    void listReturnsAllAndSupportsAuthorFilter() throws SQLException {
        dao.create(new Book(null, "Clean Code", "Uncle Bob", 2008, "X"));
        dao.create(new Book(null, "Clean Architecture", "Uncle Bob", 2017, "Y"));
        dao.create(new Book(null, "Refactoring", "Fowler", 1999, "Z"));

        List<Book> all = dao.list(null);
        assertEquals(3, all.size(), "should return all 3 books");

        List<Book> filtered = dao.list("Uncle Bob");
        assertEquals(2, filtered.size(), "author filter should match 2 books");
        assertTrue(filtered.stream().allMatch(b -> "Uncle Bob".equals(b.getAuthor())));
    }

    @Test
    void updateModifiesFieldsAndReturnsFalseForMissingId() throws SQLException {
        Book saved = dao.create(new Book(null, "Old Title", "Author", 2000, "ISBN"));
        Book patch = new Book(null, "New Title", "New Author", 2021, "NEW-ISBN");
        boolean ok = dao.update(saved.getId(), patch);
        assertTrue(ok);

        Optional<Book> fetched = dao.get(saved.getId());
        assertTrue(fetched.isPresent());
        assertEquals("New Title", fetched.get().getTitle());
        assertEquals("New Author", fetched.get().getAuthor());
        assertEquals(2021, fetched.get().getYear());
        assertEquals("NEW-ISBN", fetched.get().getIsbn());

        boolean missing = dao.update(987654321L, patch);
        assertFalse(missing, "update of nonexistent id should return false");
    }

    @Test
    void deleteRemovesRowAndReturnsFalseForMissingId() throws SQLException {
        Book saved = dao.create(new Book(null, "To Delete", "Author", 2010, "I"));
        assertTrue(dao.delete(saved.getId()));
        assertTrue(dao.get(saved.getId()).isEmpty());

        assertFalse(dao.delete(123456L), "delete of nonexistent id should return false");
    }

    @Test
    void getReturnsEmptyForMissingId() throws SQLException {
        assertTrue(dao.get(424242L).isEmpty());
    }

    @Test
    void canStoreNullYearAndIsbn() throws SQLException {
        Book saved = dao.create(new Book(null, "Title Only", "Author Only", null, null));
        Optional<Book> fetched = dao.get(saved.getId());
        assertTrue(fetched.isPresent());
        assertNull(fetched.get().getYear());
        assertNull(fetched.get().getIsbn());
    }
}
