package com.example.books;

import com.example.books.model.Book;
import com.example.books.repository.BookRepository;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
class BookRepositoryIntegrationTest {

    @Autowired
    private BookRepository bookRepository;

    @Test
    void saveAndFindById() {
        Book book = new Book("Clean Code", "Robert C. Martin", 2008, "978-0132350884");
        Book saved = bookRepository.save(book);

        assertThat(saved.getId()).isNotNull();
        assertThat(bookRepository.findById(saved.getId()))
                .isPresent()
                .get()
                .extracting(Book::getTitle, Book::getAuthor)
                .containsExactly("Clean Code", "Robert C. Martin");
    }

    @Test
    void findByAuthorReturnsOnlyMatchingBooks() {
        bookRepository.save(new Book("Book A", "Alice", 2001, "a1"));
        bookRepository.save(new Book("Book B", "Bob", 2002, "b1"));
        bookRepository.save(new Book("Book C", "Alice", 2003, "a2"));

        List<Book> byAlice = bookRepository.findByAuthor("Alice");

        assertThat(byAlice).hasSize(2);
        assertThat(byAlice).allMatch(b -> "Alice".equals(b.getAuthor()));
    }

    @Test
    void deleteRemovesBook() {
        Book saved = bookRepository.save(new Book("To Delete", "Author", 2010, "x"));
        Long id = saved.getId();

        assertThat(bookRepository.existsById(id)).isTrue();
        bookRepository.deleteById(id);
        assertThat(bookRepository.existsById(id)).isFalse();
    }
}
