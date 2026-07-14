package com.example.books;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class BookRepositoryTest {

    private BookRepository repo;
    private Path dbFile;

    @BeforeEach
    void setUp() throws Exception {
        dbFile = Files.createTempFile("repo-test-", ".db");
        repo = new BookRepository(dbFile.toString());
    }

    @AfterEach
    void tearDown() {
        repo.close();
        try {
            Files.deleteIfExists(dbFile);
        } catch (Exception e) {
            // ignore
        }
    }

    @Test
    void createAndFindById() {
        Book b = new Book(null, "1984", "George Orwell", 1949, "9780451524935");
        Book created = repo.create(b);
        assertEquals("1984", created.getTitle());
        assertTrue(created.getId() > 0);

        Optional<Book> found = repo.findById(created.getId());
        assertTrue(found.isPresent());
        assertEquals("George Orwell", found.get().getAuthor());
    }

    @Test
    void findAllFiltersByAuthor() {
        repo.create(new Book(null, "A", "Alice", 2001, null));
        repo.create(new Book(null, "B", "Bob", 2002, null));
        repo.create(new Book(null, "C", "Alice", 2003, null));

        List<Book> alice = repo.findAll("Alice");
        assertEquals(2, alice.size());

        List<Book> all = repo.findAll(null);
        assertEquals(3, all.size());
    }

    @Test
    void updateAndDelete() {
        Book b = repo.create(new Book(null, "Old", "Author", 2000, null));
        Book updated = new Book(null, "New", "Author", 2001, "isbn");
        assertTrue(repo.update(b.getId(), updated));
        assertEquals("New", repo.findById(b.getId()).get().getTitle());

        assertTrue(repo.delete(b.getId()));
        assertFalse(repo.findById(b.getId()).isPresent());
        assertFalse(repo.delete(b.getId()));
    }
}
