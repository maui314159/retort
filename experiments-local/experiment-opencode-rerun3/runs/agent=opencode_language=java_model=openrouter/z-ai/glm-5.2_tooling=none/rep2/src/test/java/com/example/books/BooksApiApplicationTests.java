package com.example.books;

import com.example.books.controller.BookController;
import com.example.books.controller.HealthController;
import com.example.books.service.BookService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.annotation.Transactional;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@Transactional
class BooksApiApplicationTests {

    @Autowired
    BookController bookController;

    @Autowired
    HealthController healthController;

    @Autowired
    BookService bookService;

    @Autowired
    JdbcTemplate jdbcTemplate;

    @Test
    void contextLoads() {
        assertThat(bookController).isNotNull();
        assertThat(healthController).isNotNull();
        assertThat(bookService).isNotNull();
    }

    @Test
    void schemaCreated() {
        Integer count = jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='books'", Integer.class);
        assertThat(count).isEqualTo(1);
    }
}
