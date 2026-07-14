package com.example.books;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class BookServiceTest {

    private static class FakeRepository extends BookRepository {
        private final List<Book> books = new ArrayList<>();

        FakeRepository() {
            super(null);
        }

        @Override
        public Optional<Book> findById(Long id) {
            return books.stream().filter(b -> b.getId().equals(id)).findFirst();
        }

        @Override
        public List<Book> findByAuthor(String author) {
            return books.stream().filter(b -> b.getAuthor().equals(author)).toList();
        }

        @Override
        public List<Book> findAll() {
            return new ArrayList<>(books);
        }

        @Override
        public Book save(Book book) {
            book.setId((long) (books.size() + 1));
            books.add(book);
            return book;
        }

        @Override
        public int update(Book book) {
            return 1;
        }

        @Override
        public int deleteById(Long id) {
            books.removeIf(b -> b.getId().equals(id));
            return 1;
        }
    }

    @Test
    void findById_throws_whenNotFound() {
        BookService service = new BookService(new FakeRepository());
        assertThatThrownBy(() -> service.findById(42L))
                .isInstanceOf(BookNotFoundException.class);
    }

    @Test
    void findAll_delegatesAuthorFilterToRepository() {
        FakeRepository repo = new FakeRepository();
        repo.save(new Book(null, "A", "Alice", 2000, "x"));
        repo.save(new Book(null, "B", "Bob", 2001, "y"));
        BookService service = new BookService(repo);

        assertThat(service.findAll("Alice")).hasSize(1);
        assertThat(service.findAll(null)).hasSize(2);
    }

    @Test
    void delete_throws_whenBookMissing() {
        BookService service = new BookService(new FakeRepository());
        assertThatThrownBy(() -> service.delete(99L))
                .isInstanceOf(BookNotFoundException.class);
    }
}
