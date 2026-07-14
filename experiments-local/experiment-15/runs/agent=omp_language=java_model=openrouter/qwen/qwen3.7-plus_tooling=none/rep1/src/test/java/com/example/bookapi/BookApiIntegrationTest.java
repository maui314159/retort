package com.example.bookapi;

import com.example.bookapi.model.Book;
import com.example.bookapi.repository.BookRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
public class BookApiIntegrationTest {

    @LocalServerPort
    private int port;

    @Autowired
    private TestRestTemplate restTemplate;

    @Autowired
    private BookRepository bookRepository;

    @BeforeEach
    public void setUp() {
        bookRepository.deleteAll();
    }

    @Test
    public void testHealthEndpoint() {
        String response = restTemplate.getForObject("http://localhost:" + port + "/health", String.class);
        assertThat(response).contains("UP");
    }

    @Test
    public void testCreateAndGetBook() {
        Book book = new Book(null, "Test Book", "Test Author", 2023, "1234567890");
        ResponseEntity<Book> response = restTemplate.postForEntity(
                "http://localhost:" + port + "/books", book, Book.class);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        assertThat(response.getBody()).isNotNull();
        assertThat(response.getBody().getTitle()).isEqualTo("Test Book");

        Long id = response.getBody().getId();
        ResponseEntity<Book> getResponse = restTemplate.getForEntity(
                "http://localhost:" + port + "/books/" + id, Book.class);
        assertThat(getResponse.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(getResponse.getBody().getAuthor()).isEqualTo("Test Author");
    }

    @Test
    public void testFilterByAuthor() {
        bookRepository.save(new Book(null, "Book A", "Author One", 2020, "111"));
        bookRepository.save(new Book(null, "Book B", "Author Two", 2021, "222"));

        ResponseEntity<Book[]> response = restTemplate.getForEntity(
                "http://localhost:" + port + "/books?author=Author+One", Book[].class);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody()).hasSize(1);
        assertThat(response.getBody()[0].getTitle()).isEqualTo("Book A");
    }

    @Test
    public void testValidationRequiresTitleAndAuthor() {
        Book invalidBook = new Book(null, "", "", 2023, "123");
        ResponseEntity<String> response = restTemplate.postForEntity(
                "http://localhost:" + port + "/books", invalidBook, String.class);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
    }

    @Test
    public void testDeleteBook() {
        Book book = bookRepository.save(new Book(null, "To Delete", "Someone", 2000, "999"));
        
        ResponseEntity<Void> deleteResponse = restTemplate.exchange(
                "http://localhost:" + port + "/books/" + book.getId(),
                org.springframework.http.HttpMethod.DELETE,
                null,
                Void.class);

        assertThat(deleteResponse.getStatusCode()).isEqualTo(HttpStatus.NO_CONTENT);
        
        ResponseEntity<Book> getResponse = restTemplate.getForEntity(
                "http://localhost:" + port + "/books/" + book.getId(), Book.class);
        assertThat(getResponse.getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
    }
}