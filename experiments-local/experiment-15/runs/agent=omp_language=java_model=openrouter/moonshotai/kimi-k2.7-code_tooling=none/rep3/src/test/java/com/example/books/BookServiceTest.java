package com.example.books;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThatThrownBy;

class BookServiceTest {

    private static class FakeRepository extends BookRepository {
        FakeRepository() {
            super(null);
        }

        @Override
        public Book create(Book book) {
            throw new AssertionError("Repository should not be called for invalid input");
        }

        @Override
        public List<Book> findAll(String author) {
            return List.of();
        }

        @Override
        public Optional<Book> findById(Long id) {
            return Optional.empty();
        }

        @Override
        public Optional<Book> update(Long id, Book book) {
            throw new AssertionError("Repository should not be called for invalid input");
        }

        @Override
        public boolean delete(Long id) {
            return false;
        }
    }

    private final BookService service = new BookService(new FakeRepository());

    @Test
    void createRejectsMissingTitle() {
        Book book = new Book(null, "  ", "Author", 2023, "123");
        assertThatThrownBy(() -> service.create(book))
            .isInstanceOf(IllegalArgumentException.class)
            .hasMessage("Title is required");
    }

    @Test
    void createRejectsMissingAuthor() {
        Book book = new Book(null, "Title", null, 2023, "123");
        assertThatThrownBy(() -> service.create(book))
            .isInstanceOf(IllegalArgumentException.class)
            .hasMessage("Author is required");
    }

    @Test
    void updateRejectsMissingTitle() {
        Book book = new Book(null, null, "Author", 2023, "123");
        assertThatThrownBy(() -> service.update(1L, book))
            .isInstanceOf(IllegalArgumentException.class)
            .hasMessage("Title is required");
    }
}
