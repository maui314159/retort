package com.example.bookapi;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Optional;

import com.example.bookapi.model.Book;
import com.example.bookapi.repository.BookRepository;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Repository-layer tests verifying CRUD behaviour directly against the JDBC
 * repository, isolated from the HTTP layer.
 */
@SpringBootTest
class BookRepositoryTest {

    private static final Path DB_FILE;

    static {
        try {
            DB_FILE = Files.createTempFile("book-api-repo", ".db");
            Files.deleteIfExists(DB_FILE);
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }

    @DynamicPropertySource
    static void datasource(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", () -> "jdbc:sqlite:" + DB_FILE);
    }

    @AfterAll
    static void cleanup() throws Exception {
        Files.deleteIfExists(DB_FILE);
    }

    @Autowired
    private BookRepository books;

    @Autowired
    private JdbcTemplate jdbc;

    @BeforeEach
    void resetTable() {
        jdbc.update("DELETE FROM books");
    }

    @Test
    void saveAssignsIdAndPersists() {
        Book saved = books.save(new Book(null, "Dune", "Herbert", 1965, "9780441172719"));

        assertThat(saved.id()).isNotNull();
        Optional<Book> fetched = books.findById(saved.id());
        assertThat(fetched).isPresent();
        assertThat(fetched.get()).usingRecursiveComparison().isEqualTo(saved);
    }

    @Test
    void findByAuthorReturnsOnlyMatches() {
        books.save(new Book(null, "Foundation", "Asimov", 1951, null));
        books.save(new Book(null, "I, Robot", "Asimov", 1950, null));
        books.save(new Book(null, "Dune", "Herbert", 1965, null));

        List<Book> asimov = books.findByAuthor("Asimov");
        assertThat(asimov).hasSize(2);
        assertThat(asimov).allSatisfy(b -> assertThat(b.author()).isEqualTo("Asimov"));

        assertThat(books.findAll()).hasSize(3);
    }

    @Test
    void updateReturnsEmptyWhenMissingAndAppliesWhenPresent() {
        assertThat(books.update(42L, new Book(42L, "X", "Y", 2000, null)))
                .isEmpty();

        Book saved = books.save(new Book(null, "Old", "Author", 1990, "old-isbn"));
        Optional<Book> updated = books.update(saved.id(),
                new Book(saved.id(), "New", "Author", 1990, "new-isbn"));

        assertThat(updated).isPresent();
        assertThat(updated.get().title()).isEqualTo("New");
        assertThat(updated.get().isbn()).isEqualTo("new-isbn");
        assertThat(books.findById(saved.id()).orElseThrow().title()).isEqualTo("New");
    }

    @Test
    void deleteByIdReportsExistence() {
        Book saved = books.save(new Book(null, "Tmp", "Author", 2000, null));

        assertThat(books.deleteById(999L)).isFalse();
        assertThat(books.deleteById(saved.id())).isTrue();
        assertThat(books.findById(saved.id())).isEmpty();
    }
}
