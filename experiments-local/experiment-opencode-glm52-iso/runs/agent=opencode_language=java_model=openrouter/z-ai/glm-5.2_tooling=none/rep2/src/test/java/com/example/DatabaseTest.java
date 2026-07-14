package com.example;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.sql.SQLException;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class DatabaseTest {

    private Database db;

    @BeforeEach
    void setUp() throws SQLException {
        db = new Database("jdbc:sqlite::memory:");
    }

    @AfterEach
    void tearDown() throws SQLException {
        db.close();
    }

    @Test
    void insertAssignsIdAndPersists() throws SQLException {
        Book b = new Book(null, "The Hobbit", "J.R.R. Tolkien", 1937, "978-0261102217");
        db.insert(b);
        assertNotNull(b.getId(), "inserted book should get an id");

        Book fetched = db.findById(b.getId());
        assertNotNull(fetched);
        assertEquals("The Hobbit", fetched.getTitle());
        assertEquals("J.R.R. Tolkien", fetched.getAuthor());
        assertEquals(1937, fetched.getYear());
        assertEquals("978-0261102217", fetched.getIsbn());
    }

    @Test
    void findAllReturnsAllAndFilterByAuthor() throws SQLException {
        db.insert(new Book(null, "Book A", "Alice", 2001, null));
        db.insert(new Book(null, "Book B", "Bob", 2002, null));
        db.insert(new Book(null, "Book C", "Alice", 2003, null));

        assertEquals(3, db.findAll(null).size());
        List<Book> alice = db.findAll("Alice");
        assertEquals(2, alice.size());
        assertTrue(alice.stream().allMatch(b -> b.getAuthor().equals("Alice")));
    }

    @Test
    void updateAndDeleteWork() throws SQLException {
        Book b = db.insert(new Book(null, "Old", "Alice", 2000, "x"));
        assertTrue(db.update(b.getId(), new Book(null, "New", "Bob", 2010, "y")));
        Book updated = db.findById(b.getId());
        assertEquals("New", updated.getTitle());
        assertEquals("Bob", updated.getAuthor());
        assertEquals(2010, updated.getYear());

        assertTrue(db.delete(b.getId()));
        assertNull(db.findById(b.getId()));
        assertFalse(db.delete(999L), "deleting non-existent should return false");
    }
}
