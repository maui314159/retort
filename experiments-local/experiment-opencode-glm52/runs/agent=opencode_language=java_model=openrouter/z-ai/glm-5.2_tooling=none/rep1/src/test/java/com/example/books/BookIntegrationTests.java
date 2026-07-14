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
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.TestPropertySource;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@TestPropertySource(properties = {
        "spring.datasource.url=jdbc:sqlite::memory:",
        "spring.datasource.hikari.maximum-pool-size=1"
})
class BookIntegrationTests {

    @Autowired
    TestRestTemplate rest;

    @Autowired
    JdbcTemplate jdbc;

    @BeforeEach
    void cleanDb() {
        jdbc.execute("DELETE FROM books");
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> body(ResponseEntity<Map> resp) {
        return (Map<String, Object>) resp.getBody();
    }

    @Test
    void healthEndpointReturnsUp() {
        ResponseEntity<Map> resp = rest.getForEntity("/health", Map.class);
        assertThat(resp.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(body(resp).get("status")).isEqualTo("UP");
    }

    @Test
    void createListGetUpdateDelete_lifecycle() {
        Book book = new Book(null, "The Pragmatic Programmer", "Hunt & Thomas", 1999, "9780201616224");

        // CREATE
        ResponseEntity<Book> post = rest.postForEntity("/books", book, Book.class);
        assertThat(post.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        Long id = post.getBody().getId();
        assertThat(post.getBody().getTitle()).isEqualTo("The Pragmatic Programmer");

        // GET by id
        ResponseEntity<Book> get = rest.getForEntity("/books/" + id, Book.class);
        assertThat(get.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(get.getBody().getAuthor()).isEqualTo("Hunt & Thomas");

        // LIST all
        ResponseEntity<Book[]> list = rest.getForEntity("/books", Book[].class);
        assertThat(list.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(list.getBody()).hasSize(1);
        assertThat(list.getBody()[0].getTitle()).isEqualTo("The Pragmatic Programmer");

        // UPDATE
        Book updated = new Book(null, "The Pragmatic Programmer (2nd)", "Hunt & Thomas", 2019, "9780135956 159");
        ResponseEntity<Book> put = rest.exchange("/books/" + id, HttpMethod.PUT,
                new HttpEntity<>(updated), Book.class);
        assertThat(put.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(put.getBody().getTitle()).isEqualTo("The Pragmatic Programmer (2nd)");
        assertThat(put.getBody().getYear()).isEqualTo(2019);

        // DELETE
        ResponseEntity<Void> del = rest.exchange("/books/" + id, HttpMethod.DELETE,
                new HttpEntity<>(null), Void.class);
        assertThat(del.getStatusCode()).isEqualTo(HttpStatus.NO_CONTENT);
        ResponseEntity<Map> after = rest.getForEntity("/books/" + id, Map.class);
        assertThat(after.getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
    }

    @Test
    void validationRejectsMissingTitleAndAuthor() {
        // missing title and author
        Book bad = new Book(null, null, null, 2020, "x");
        ResponseEntity<Map> r1 = rest.postForEntity("/books", bad, Map.class);
        assertThat(r1.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        assertThat((String) body(r1).get("message")).contains("title");

        // missing author only
        Book bad2 = new Book(null, "Title Only", null, 2020, null);
        ResponseEntity<Map> r2 = rest.postForEntity("/books", bad2, Map.class);
        assertThat(r2.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        assertThat((String) body(r2).get("message")).contains("author");
    }

    @Test
    void listSupportsAuthorFilter() {
        create(new Book(null, "Refactoring", "Fowler", 1999, "1"));
        create(new Book(null, "UML Distilled", "Fowler", 2003, "2"));
        create(new Book(null, "Clean Code", "Martin", 2008, "3"));

        ResponseEntity<Book[]> resp = rest.getForEntity("/books?author=Fowler", Book[].class);
        assertThat(resp.getStatusCode()).isEqualTo(HttpStatus.OK);
        List<Book> books = List.of(resp.getBody());
        assertThat(books).hasSize(2);
        assertThat(books).allSatisfy(b -> assertThat(b.getAuthor()).isEqualTo("Fowler"));
    }

    @Test
    void deleteOfMissingReturnsNotFound() {
        ResponseEntity<Map> resp = rest.exchange("/books/999999", HttpMethod.DELETE,
                new HttpEntity<>(null), Map.class);
        assertThat(resp.getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
    }

    private void create(Book b) {
        ResponseEntity<Book> r = rest.postForEntity("/books", b, Book.class);
        assertThat(r.getStatusCode()).isEqualTo(HttpStatus.CREATED);
    }
}
