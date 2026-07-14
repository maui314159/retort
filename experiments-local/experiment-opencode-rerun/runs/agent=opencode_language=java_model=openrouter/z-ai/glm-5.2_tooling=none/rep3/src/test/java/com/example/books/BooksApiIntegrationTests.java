package com.example.books;

import com.example.books.model.Book;
import com.example.books.repository.BookRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class BooksApiIntegrationTests {

    @LocalServerPort
    private int port;

    @Autowired
    private TestRestTemplate restTemplate;

    @Autowired
    private BookRepository repository;

    private String baseUrl() {
        return "http://localhost:" + port + "/books";
    }

    @BeforeEach
    void cleanup() {
        repository.deleteAll();
    }

    @Test
    void createBook_returns201AndPersists() {
        Book book = new Book(null, "The Pragmatic Programmer", "Hunt", 2019, "978-0135957059");

        ResponseEntity<Book> response = restTemplate.postForEntity(baseUrl(), book, Book.class);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        assertThat(response.getBody()).isNotNull();
        assertThat(response.getBody().getId()).isNotNull();
        assertThat(response.getBody().getTitle()).isEqualTo("The Pragmatic Programmer");
        assertThat(repository.count()).isEqualTo(1);
    }

    @Test
    void createBook_rejectsMissingTitleWith400() {
        Book book = new Book(null, "", "Author", 2020, "x");

        ResponseEntity<Map<String, Object>> response = restTemplate.exchange(
                baseUrl(),
                HttpMethod.POST,
                new HttpEntity<>(book),
                new ParameterizedTypeReference<>() {
                });

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        assertThat(response.getBody()).isNotNull();
        assertThat(response.getBody().get("status")).isEqualTo(400);
        @SuppressWarnings("unchecked")
        Map<String, String> details = (Map<String, String>) response.getBody().get("details");
        assertThat(details).containsKey("title");
        assertThat(repository.count()).isEqualTo(0);
    }

    @Test
    void listBooks_filtersByAuthor() {
        repository.save(new Book(null, "Refactoring", "Fowler", 1999, "a"));
        repository.save(new Book(null, "Clean Code", "Martin", 2008, "b"));
        repository.save(new Book(null, "UML Distilled", "Fowler", 2003, "c"));

        ResponseEntity<List<Book>> response = restTemplate.exchange(
                baseUrl() + "?author=Fowler",
                HttpMethod.GET,
                null,
                new ParameterizedTypeReference<>() {
                });

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody()).isNotNull();
        assertThat(response.getBody()).hasSize(2);
        assertThat(response.getBody()).allSatisfy(b -> assertThat(b.getAuthor()).isEqualTo("Fowler"));
    }

    @Test
    void getBook_returns404WhenNotFound() {
        ResponseEntity<Map<String, Object>> response = restTemplate.exchange(
                baseUrl() + "/9999",
                HttpMethod.GET,
                null,
                new ParameterizedTypeReference<>() {
                });

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
        assertThat(response.getBody()).isNotNull();
        assertThat(response.getBody().get("status")).isEqualTo(404);
    }

    @Test
    void updateBook_modifiesExistingRecord() {
        Book saved = repository.save(new Book(null, "Old Title", "Old Author", 2000, "old"));

        Book incoming = new Book(null, "New Title", "New Author", 2021, "new");
        ResponseEntity<Book> response = restTemplate.exchange(
                baseUrl() + "/" + saved.getId(),
                HttpMethod.PUT,
                new HttpEntity<>(incoming),
                Book.class);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody()).isNotNull();
        assertThat(response.getBody().getTitle()).isEqualTo("New Title");
        assertThat(response.getBody().getAuthor()).isEqualTo("New Author");
        assertThat(repository.findById(saved.getId())).isPresent()
                .get().extracting(Book::getTitle).isEqualTo("New Title");
    }

    @Test
    void deleteBook_removesRecordAndReturns204() {
        Book saved = repository.save(new Book(null, "Tmp", "A", 2020, "x"));

        ResponseEntity<Void> response = restTemplate.exchange(
                baseUrl() + "/" + saved.getId(),
                HttpMethod.DELETE,
                null,
                Void.class);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.NO_CONTENT);
        assertThat(repository.existsById(saved.getId())).isFalse();
    }

    @Test
    void healthEndpoint_returnsUp() {
        ResponseEntity<Map<String, Object>> response = restTemplate.exchange(
                "http://localhost:" + port + "/health",
                HttpMethod.GET,
                null,
                new ParameterizedTypeReference<>() {
                });

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody()).containsEntry("status", "UP");
    }
}
