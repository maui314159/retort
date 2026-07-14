package com.example.books.repository;

import com.example.books.model.Book;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.test.context.ActiveProfiles;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@ActiveProfiles("test")
class BookRepositoryTest {

    @Autowired
    private BookRepository bookRepository;

    @AfterEach
    void cleanup() {
        bookRepository.deleteAll();
    }

    @Test
    void findByAuthorContainingIgnoreCaseMatchesCaseInsensitively() {
        bookRepository.save(new Book(null, "T1", "Alice Walker", 2001, "a"));
        bookRepository.save(new Book(null, "T2", "alice cooper", 2002, "b"));
        bookRepository.save(new Book(null, "T3", "Bob", 2003, "c"));

        List<Book> found = bookRepository.findByAuthorContainingIgnoreCase("ALICE");

        assertThat(found).hasSize(2);
        assertThat(found).extracting(Book::getAuthor)
                .containsExactlyInAnyOrder("Alice Walker", "alice cooper");
    }
}
