package com.example.books;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class BookControllerIntegrationTest {

    @Autowired
    private TestRestTemplate rest;

    @Autowired
    private JdbcTemplate jdbc;

    @BeforeEach
    void setUp() {
        jdbc.update("DELETE FROM books");
    }

    @Test
    void healthEndpointReturnsUp() {
        ResponseEntity<Map<String, String>> response = rest.exchange(
            "/health", HttpMethod.GET, null, new ParameterizedTypeReference<>() {}
        );
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody()).containsEntry("status", "UP");
    }

    @Test
    void createBookReturns201AndPersistsBook() {
        Book request = new Book(null, "Clean Code", "Robert C. Martin", 2008, "9780132350884");

        ResponseEntity<Book> response = rest.postForEntity("/books", request, Book.class);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        assertThat(response.getBody()).isNotNull();
        assertThat(response.getBody().id()).isNotNull();
        assertThat(response.getBody().title()).isEqualTo("Clean Code");
    }

    @Test
    void listBooksSupportsAuthorFilter() {
        rest.postForEntity("/books", new Book(null, "Book A", "Alice", 2020, "111"), Book.class);
        rest.postForEntity("/books", new Book(null, "Book B", "Bob", 2021, "222"), Book.class);

        ResponseEntity<List<Book>> response = rest.exchange(
            "/books?author=Alice", HttpMethod.GET, null, new ParameterizedTypeReference<>() {}
        );

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody()).hasSize(1);
        assertThat(response.getBody().get(0).author()).isEqualTo("Alice");
    }

    @Test
    void getBookByIdReturns404WhenMissing() {
        ResponseEntity<Book> response = rest.getForEntity("/books/9999", Book.class);
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
    }

    @Test
    void updateAndDeleteBook() {
        Book created = rest.postForEntity("/books", new Book(null, "Refactoring", "Martin Fowler", 1999, "123"), Book.class).getBody();
        assertThat(created).isNotNull();

        Book update = new Book(null, "Refactoring", "Martin Fowler", 2018, "9780134757599");
        ResponseEntity<Book> updated = rest.exchange(
            "/books/" + created.id(), HttpMethod.PUT, new HttpEntity<>(update), Book.class
        );
        assertThat(updated.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(updated.getBody().year()).isEqualTo(2018);

        ResponseEntity<Void> deleted = rest.exchange(
            "/books/" + created.id(), HttpMethod.DELETE, null, Void.class
        );
        assertThat(deleted.getStatusCode()).isEqualTo(HttpStatus.NO_CONTENT);

        assertThat(rest.getForEntity("/books/" + created.id(), Book.class).getStatusCode())
            .isEqualTo(HttpStatus.NOT_FOUND);
    }

    @Test
    void createBookWithoutTitleReturns400() {
        Book request = new Book(null, "", "Author", 2023, "000");
        ResponseEntity<Map<String, String>> response = rest.exchange(
            "/books", HttpMethod.POST, new HttpEntity<>(request), new ParameterizedTypeReference<>() {}
        );
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        assertThat(response.getBody()).containsEntry("error", "Title is required");
    }
}
