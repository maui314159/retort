package com.example.books;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class BookControllerTest {

    @Autowired
    private TestRestTemplate restTemplate;

    @Autowired
    private BookRepository bookRepository;

    @BeforeEach
    void setUp() {
        bookRepository.deleteAll();
    }

    @Test
    void healthReturnsUp() {
        ResponseEntity<Map> response = restTemplate.getForEntity("/health", Map.class);
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody()).containsEntry("status", "up");
    }

    @Test
    void createBookReturns201AndSavesBook() {
        Book book = new Book("The Hobbit", "J.R.R. Tolkien", 1937, "978-0547928227");

        ResponseEntity<Book> response = restTemplate.postForEntity("/books", book, Book.class);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        assertThat(response.getBody()).isNotNull();
        assertThat(response.getBody().getId()).isNotNull();
        assertThat(response.getBody().getTitle()).isEqualTo("The Hobbit");
    }

    @Test
    void createBookWithoutTitleReturns400() {
        Book book = new Book(null, "Author", 2020, "123");

        ResponseEntity<Map> response = restTemplate.postForEntity("/books", book, Map.class);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        assertThat(response.getBody()).containsKey("title");
    }

    @Test
    void listBooksSupportsAuthorFilter() {
        bookRepository.save(new Book("Book One", "Alice Smith", 2020, "111"));
        bookRepository.save(new Book("Book Two", "Bob Jones", 2021, "222"));

        ResponseEntity<List> response = restTemplate.getForEntity("/books?author=alice", List.class);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody()).hasSize(1);
    }

    @Test
    void getBookReturns404WhenMissing() {
        ResponseEntity<Book> response = restTemplate.getForEntity("/books/9999", Book.class);
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
    }

    @Test
    void updateBookModifiesExistingBook() {
        Book saved = bookRepository.save(new Book("Old Title", "Old Author", 2000, "000"));
        Book update = new Book("New Title", "New Author", 2022, "999");

        ResponseEntity<Book> response = restTemplate.exchange(
                "/books/" + saved.getId(),
                HttpMethod.PUT,
                new HttpEntity<>(update),
                Book.class
        );

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody().getTitle()).isEqualTo("New Title");
    }

    @Test
    void deleteBookRemovesBook() {
        Book saved = bookRepository.save(new Book("To Delete", "Author", 1999, "333"));

        ResponseEntity<Void> response = restTemplate.exchange(
                "/books/" + saved.getId(),
                HttpMethod.DELETE,
                null,
                Void.class
        );

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.NO_CONTENT);
        assertThat(bookRepository.existsById(saved.getId())).isFalse();
    }
}
