package com.example.bookapi;

import java.util.Map;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.http.*;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class BookApiIntegrationTests {

    @Autowired
    private TestRestTemplate rest;

    private ResponseEntity<Map> postBook(String title, String author, Integer year, String isbn) {
        Map<String, Object> body = new java.util.HashMap<>();
        if (title != null) body.put("title", title);
        if (author != null) body.put("author", author);
        if (year != null) body.put("year", year);
        if (isbn != null) body.put("isbn", isbn);
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        return rest.postForEntity("/books", new HttpEntity<>(body, headers), Map.class);
    }

    @Test
    void createBook_returns201WithBody() {
        ResponseEntity<Map> resp = postBook("The Hobbit", "J.R.R. Tolkien", 1937, "978-0261103283");
        assertThat(resp.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        assertThat(resp.getBody()).isNotNull();
        assertThat(resp.getBody().get("title")).isEqualTo("The Hobbit");
        assertThat(resp.getBody().get("author")).isEqualTo("J.R.R. Tolkien");
        assertThat(resp.getBody().get("year")).isEqualTo(1937);
        assertThat(resp.getBody().get("id")).isNotNull();
    }

    @Test
    void createBook_missingTitle_returns400() {
        ResponseEntity<Map> resp = postBook(null, "Some Author", 2000, "isbn-1");
        assertThat(resp.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        assertThat(resp.getBody()).isNotNull();
        assertThat(resp.getBody().toString()).contains("title");
    }

    @Test
    void createBook_missingAuthor_returns400() {
        ResponseEntity<Map> resp = postBook("Some Title", null, 2000, "isbn-2");
        assertThat(resp.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        assertThat(resp.getBody()).toString().contains("author");
    }

    @Test
    void lifecycle_createGetListUpdateDelete() {
        // create
        ResponseEntity<Map> created = postBook("Dune", "Frank Herbert", 1965, "978-0441172719");
        Long id = ((Number) created.getBody().get("id")).longValue();

        // get by id
        ResponseEntity<Map> got = rest.getForEntity("/books/" + id, Map.class);
        assertThat(got.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(got.getBody().get("title")).isEqualTo("Dune");

        // list all contains it
        ResponseEntity<Map[]> list = rest.getForEntity("/books", Map[].class);
        assertThat(list.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(list.getBody()).isNotEmpty();

        // update
        Map<String, Object> update = Map.of("title", "Dune Updated", "author", "Frank Herbert",
                "year", 1966, "isbn", "978-0441172719");
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        ResponseEntity<Map> updated = rest.exchange("/books/" + id, HttpMethod.PUT,
                new HttpEntity<>(update, headers), Map.class);
        assertThat(updated.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(updated.getBody().get("title")).isEqualTo("Dune Updated");
        assertThat(updated.getBody().get("year")).isEqualTo(1966);

        // delete
        ResponseEntity<Void> deleted = rest.exchange("/books/" + id, HttpMethod.DELETE,
                HttpEntity.EMPTY, Void.class);
        assertThat(deleted.getStatusCode()).isEqualTo(HttpStatus.NO_CONTENT);

        // get after delete -> 404
        ResponseEntity<Void> after = rest.getForEntity("/books/" + id, Void.class);
        assertThat(after.getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
    }

    @Test
    void getNonexistentBook_returns404() {
        ResponseEntity<Void> resp = rest.getForEntity("/books/999999", Void.class);
        assertThat(resp.getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
    }

    @Test
    void authorFilter_returnsOnlyMatching() {
        postBook("Book A", "Author X", 2001, "a");
        postBook("Book B", "Author Y", 2002, "b");
        postBook("Book C", "Author X", 2003, "c");

        ResponseEntity<Map[]> filtered = rest.getForEntity("/books?author=Author X", Map[].class);
        assertThat(filtered.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(filtered.getBody()).isNotNull();
        assertThat(filtered.getBody().length).isEqualTo(2);
        for (Map<?, ?> b : filtered.getBody()) {
            assertThat(b.get("author")).isEqualTo("Author X");
        }
    }

    @Test
    void updateNonexistentBook_returns404() {
        Map<String, Object> update = Map.of("title", "Ghost", "author", "Nobody", "year", 0, "isbn", "x");
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        ResponseEntity<Map> resp = rest.exchange("/books/888888", HttpMethod.PUT,
                new HttpEntity<>(update, headers), Map.class);
        assertThat(resp.getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
    }

    @Test
    void deleteNonexistentBook_returns404() {
        ResponseEntity<Void> resp = rest.exchange("/books/777777", HttpMethod.DELETE,
                HttpEntity.EMPTY, Void.class);
        assertThat(resp.getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
    }

    @Test
    void healthEndpoint_returnsUp() {
        ResponseEntity<Map> resp = rest.getForEntity("/health", Map.class);
        assertThat(resp.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(resp.getBody().get("status")).isEqualTo("UP");
    }
}
