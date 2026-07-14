package com.example.books.service;

import com.example.books.model.Book;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@Transactional
class BookServiceTests {

    @Autowired
    BookService bookService;

    @Test
    void createAndFindById() {
        Book book = new Book(null, "The Hobbit", "J.R.R. Tolkien", 1937, "978-0261103283");
        Book created = bookService.create(book);
        assertThat(created.getId()).isNotNull();

        Optional<Book> fetched = bookService.findById(created.getId());
        assertThat(fetched).isPresent();
        assertThat(fetched.get().getTitle()).isEqualTo("The Hobbit");
        assertThat(fetched.get().getAuthor()).isEqualTo("J.R.R. Tolkien");
        assertThat(fetched.get().getYear()).isEqualTo(1937);
        assertThat(fetched.get().getIsbn()).isEqualTo("978-0261103283");
    }

    @Test
    void findByAuthorFilters() {
        bookService.create(new Book(null, "Book A", "Alice", 2001, "111"));
        bookService.create(new Book(null, "Book B", "Bob", 2002, "222"));
        bookService.create(new Book(null, "Book C", "Alice", 2003, "333"));

        List<Book> aliceBooks = bookService.findByAuthor("Alice");
        assertThat(aliceBooks).hasSize(2);
        assertThat(aliceBooks).allSatisfy(b -> assertThat(b.getAuthor()).isEqualTo("Alice"));
    }

    @Test
    void updateChangesFields() {
        Book created = bookService.create(new Book(null, "Old Title", "Old Author", 1999, "000"));
        Book update = new Book(null, "New Title", "New Author", 2020, "999");
        Optional<Book> updated = bookService.update(created.getId(), update);

        assertThat(updated).isPresent();
        assertThat(updated.get().getTitle()).isEqualTo("New Title");
        assertThat(updated.get().getAuthor()).isEqualTo("New Author");
        assertThat(updated.get().getYear()).isEqualTo(2020);
        assertThat(updated.get().getId()).isEqualTo(created.getId());
    }

    @Test
    void updateNonexistentReturnsEmpty() {
        Optional<Book> updated = bookService.update(999999L, new Book(null, "X", "Y", 1, "Z"));
        assertThat(updated).isEmpty();
    }

    @Test
    void deleteRemovesBook() {
        Book created = bookService.create(new Book(null, "To Delete", "Author", 2010, "555"));
        boolean deleted = bookService.delete(created.getId());
        assertThat(deleted).isTrue();
        assertThat(bookService.findById(created.getId())).isEmpty();
    }

    @Test
    void deleteNonexistentReturnsFalse() {
        assertThat(bookService.delete(999999L)).isFalse();
    }
}
