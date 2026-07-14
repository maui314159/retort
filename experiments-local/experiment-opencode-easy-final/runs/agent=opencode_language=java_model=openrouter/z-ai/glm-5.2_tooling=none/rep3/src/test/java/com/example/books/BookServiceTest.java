package com.example.books;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicLong;

import static org.junit.jupiter.api.Assertions.*;

class BookServiceTest {

    private FakeRepository repository;
    private BookService service;

    @BeforeEach
    void setUp() {
        repository = new FakeRepository();
        service = new BookService(repository);
    }

    @Test
    void createSavesAndReturnsBookWithId() {
        Book input = new Book(null, "Title", "Author", 2000, "ISBN");

        Book result = service.create(input);

        assertNotNull(result.getId());
        assertEquals("Title", result.getTitle());
        assertTrue(repository.saved.contains(input));
    }

    @Test
    void findAllWithAuthorDelegatesToFindByAuthor() {
        repository.stored.add(new Book(1L, "T", "Frank Herbert", 1965, "x"));

        List<Book> result = service.findAll("Frank Herbert");

        assertEquals(1, result.size());
        assertEquals("Frank Herbert", result.get(0).getAuthor());
        assertEquals(0, repository.findAllCallCount);
    }

    @Test
    void findAllWithoutAuthorReturnsAll() {
        repository.stored.add(new Book(1L, "A", "X", 2000, "i"));
        repository.stored.add(new Book(2L, "B", "Y", 2001, "j"));

        List<Book> result = service.findAll(null);

        assertEquals(2, result.size());
        assertEquals(1, repository.findAllCallCount);
    }

    @Test
    void findAllWithBlankAuthorReturnsAll() {
        repository.stored.add(new Book(1L, "A", "X", 2000, "i"));

        List<Book> result = service.findAll("   ");

        assertEquals(1, result.size());
        assertEquals(1, repository.findAllCallCount);
    }

    @Test
    void findByIdThrowsWhenMissing() {
        assertThrows(BookNotFoundException.class, () -> service.findById(99L));
    }

    @Test
    void updateOverwritesFieldsOfExistingBook() {
        Book existing = new Book(1L, "Old", "OldAuthor", 1900, "old-isbn");
        repository.stored.add(existing);

        Book incoming = new Book(null, "New", "NewAuthor", 2020, "new-isbn");
        Book result = service.update(1L, incoming);

        assertEquals(1L, result.getId());
        assertEquals("New", result.getTitle());
        assertEquals("NewAuthor", result.getAuthor());
        assertEquals(2020, result.getYear());
        assertEquals("new-isbn", result.getIsbn());
        assertEquals(1, repository.updateCallCount);
    }

    @Test
    void updateThrowsWhenMissing() {
        Book incoming = new Book(null, "New", "NewAuthor", 2020, "new-isbn");
        assertThrows(BookNotFoundException.class, () -> service.update(1L, incoming));
    }

    @Test
    void deleteDelegatesToRepository() {
        service.delete(5L);
        assertEquals(5L, repository.deletedId);
    }

    static class FakeRepository extends BookRepository {
        final List<Book> stored = new ArrayList<>();
        final List<Book> saved = new ArrayList<>();
        final AtomicLong idSeq = new AtomicLong(100);
        int findAllCallCount;
        int updateCallCount;
        Long deletedId;

        FakeRepository() {
            super(null);
        }

        @Override
        public Book save(Book book) {
            book.setId(idSeq.incrementAndGet());
            stored.add(book);
            saved.add(book);
            return book;
        }

        @Override
        public Optional<Book> findById(Long id) {
            return stored.stream().filter(b -> b.getId().equals(id)).findFirst();
        }

        @Override
        public List<Book> findAll() {
            findAllCallCount++;
            return new ArrayList<>(stored);
        }

        @Override
        public List<Book> findByAuthor(String author) {
            return stored.stream().filter(b -> b.getAuthor().equals(author)).toList();
        }

        @Override
        public int update(Book book) {
            updateCallCount++;
            return 1;
        }

        @Override
        public int deleteById(Long id) {
            deletedId = id;
            stored.removeIf(b -> b.getId().equals(id));
            return 1;
        }
    }
}
