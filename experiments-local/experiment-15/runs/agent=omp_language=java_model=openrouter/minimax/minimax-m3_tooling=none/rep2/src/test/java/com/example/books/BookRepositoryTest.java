package com.example.books;

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
        "spring.sql.init.mode=always"
})
class BookRepositoryTest {

    @Autowired private BookRepository repo;
    @Autowired private JdbcTemplate jdbc;

    @BeforeEach
    void clean() {
        jdbc.update("DELETE FROM book");
    }

    @Test
    void saveAssignsIdAndRoundTripsFields() {
        Book b = new Book(null, "Dune", "Frank Herbert", 1965, "0441172717");
        Book saved = repo.save(b);
        assertThat(saved.getId()).isNotNull().isPositive();

        Book fetched = repo.findById(saved.getId()).orElseThrow();
        assertThat(fetched.getTitle()).isEqualTo("Dune");
        assertThat(fetched.getAuthor()).isEqualTo("Frank Herbert");
        assertThat(fetched.getYear()).isEqualTo(1965);
        assertThat(fetched.getIsbn()).isEqualTo("0441172717");
    }

    @Test
    void nullYearIsStoredAsNull() {
        Book saved = repo.save(new Book(null, "Untitled", "Anon", null, null));
        Book fetched = repo.findById(saved.getId()).orElseThrow();
        assertThat(fetched.getYear()).isNull();
        assertThat(fetched.getIsbn()).isNull();
    }

    @Test
    void findAllWithoutFilterReturnsAllBooksOrderedById() {
        repo.save(new Book(null, "A", "Alice", 2000, null));
        repo.save(new Book(null, "B", "Bob", 2001, null));
        repo.save(new Book(null, "C", "Alice", 2002, null));

        List<Book> all = repo.findAll(null);
        assertThat(all).hasSize(3);
        assertThat(all).extracting(Book::getTitle).containsExactly("A", "B", "C");
    }

    @Test
    void findAllWithAuthorFilterReturnsMatches() {
        repo.save(new Book(null, "A", "Alice", 2000, null));
        repo.save(new Book(null, "B", "Bob", 2001, null));
        repo.save(new Book(null, "C", "Alice", 2002, null));

        List<Book> alice = repo.findAll("Alice");
        assertThat(alice).hasSize(2);
        assertThat(alice).allMatch(b -> "Alice".equals(b.getAuthor()));
    }

    @Test
    void updateChangesFieldsAndReturnsTrue() {
        Book saved = repo.save(new Book(null, "Old", "Alice", 2000, "111"));
        boolean ok = repo.update(saved.getId(), new Book(null, "New", "Alice", 2024, "222"));

        assertThat(ok).isTrue();
        Book fetched = repo.findById(saved.getId()).orElseThrow();
        assertThat(fetched.getTitle()).isEqualTo("New");
        assertThat(fetched.getYear()).isEqualTo(2024);
        assertThat(fetched.getIsbn()).isEqualTo("222");
    }

    @Test
    void updateMissingIdReturnsFalse() {
        boolean ok = repo.update(9999L, new Book(null, "x", "y", null, null));
        assertThat(ok).isFalse();
    }

    @Test
    void deleteRemovesRowAndReturnsTrueThenFalse() {
        Book saved = repo.save(new Book(null, "X", "Y", null, null));
        assertThat(repo.delete(saved.getId())).isTrue();
        assertThat(repo.findById(saved.getId())).isEqualTo(Optional.empty());
        assertThat(repo.delete(saved.getId())).isFalse();
    }
}
