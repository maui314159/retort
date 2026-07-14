package com.example.books;

import com.example.books.dto.BookRequest;
import com.example.books.model.Book;
import com.example.books.repository.BookRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.TestPropertySource;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@TestPropertySource(properties = {
        "spring.datasource.url=jdbc:sqlite::memory:",
        "spring.datasource.driver-class-name=org.sqlite.JDBC",
        "spring.datasource.hikari.maximum-pool-size=1",
        "spring.sql.init.mode=always"
})
class BookRepositoryTest {

    @Autowired
    BookRepository repository;

    @Autowired
    JdbcTemplate jdbc;

    @BeforeEach
    void reset() {
        jdbc.update("DELETE FROM books");
    }

    @Test
    void saveAssignsIdAndPersists() {
        Book saved = repository.save(new Book(null, "Dune", "Herbert", 1965, "isbn-1"));
        assertThat(saved.id()).isNotNull();
        Optional<Book> fetched = repository.findById(saved.id());
        assertThat(fetched).isPresent();
        assertThat(fetched.get().title()).isEqualTo("Dune");
        assertThat(fetched.get().year()).isEqualTo(1965);
    }

    @Test
    void findAllFiltersByAuthor() {
        repository.save(new Book(null, "Dune", "Herbert", 1965, "a"));
        repository.save(new Book(null, "Foundation", "Asimov", 1951, "b"));
        repository.save(new Book(null, "God Emperor", "Herbert", 1981, "c"));

        List<Book> all = repository.findAll(null);
        assertThat(all).hasSize(3);

        List<Book> herbert = repository.findAll("Herbert");
        assertThat(herbert).hasSize(2);
        assertThat(herbert).allSatisfy(b -> assertThat(b.author()).isEqualTo("Herbert"));
    }

    @Test
    void updateAndDeleteWork() {
        Book saved = repository.save(new Book(null, "Old", "Auth", 2000, "x"));
        boolean updated = repository.update(saved.id(),
                new Book(saved.id(), "New", "Auth", 2001, "x"));
        assertThat(updated).isTrue();
        assertThat(repository.findById(saved.id()).orElseThrow().title()).isEqualTo("New");

        boolean deleted = repository.deleteById(saved.id());
        assertThat(deleted).isTrue();
        assertThat(repository.findById(saved.id())).isEmpty();
    }
}
