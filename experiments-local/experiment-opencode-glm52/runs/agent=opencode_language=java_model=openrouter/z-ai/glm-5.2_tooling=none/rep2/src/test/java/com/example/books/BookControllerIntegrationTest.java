package com.example.books;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.*;
import org.springframework.test.context.jdbc.Sql;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Sql(scripts = "/cleanup.sql")
class BookControllerIntegrationTest {

    @Autowired
    TestRestTemplate rest;

    private static final ParameterizedTypeReference<Map<String, Object>> MAP =
            new ParameterizedTypeReference<>() {};
    private static final ParameterizedTypeReference<List<Map<String, Object>>> LIST =
            new ParameterizedTypeReference<>() {};

    @Test
    void createListGetUpdateDelete_bookLifecycle() {
        // Create
        Map<String, Object> payload = Map.of(
                "title", "The Hobbit",
                "author", "J.R.R. Tolkien",
                "year", 1937,
                "isbn", "978-0261103283");
        ResponseEntity<Map<String, Object>> created = rest.exchange(
                "/books", HttpMethod.POST, new HttpEntity<>(payload), MAP);
        assertThat(created.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        Number id = (Number) created.getBody().get("id");
        assertThat(id).isNotNull();
        assertThat(created.getBody().get("title")).isEqualTo("The Hobbit");

        // Get single
        ResponseEntity<Map<String, Object>> fetched = rest.exchange(
                "/books/" + id, HttpMethod.GET, null, MAP);
        assertThat(fetched.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(fetched.getBody().get("author")).isEqualTo("J.R.R. Tolkien");

        // List
        ResponseEntity<List<Map<String, Object>>> list = rest.exchange(
                "/books", HttpMethod.GET, null, LIST);
        assertThat(list.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(list.getBody()).hasSize(1);

        // Update
        Map<String, Object> update = Map.of(
                "title", "The Hobbit Revised",
                "author", "J.R.R. Tolkien",
                "year", 1937,
                "isbn", "978-0261103283");
        ResponseEntity<Map<String, Object>> updated = rest.exchange(
                "/books/" + id, HttpMethod.PUT, new HttpEntity<>(update), MAP);
        assertThat(updated.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(updated.getBody().get("title")).isEqualTo("The Hobbit Revised");

        // Delete
        ResponseEntity<Void> deleted = rest.exchange(
                "/books/" + id, HttpMethod.DELETE, null, Void.class);
        assertThat(deleted.getStatusCode()).isEqualTo(HttpStatus.NO_CONTENT);

        // Get after delete -> 404
        ResponseEntity<Map<String, Object>> after = rest.exchange(
                "/books/" + id, HttpMethod.GET, null, MAP);
        assertThat(after.getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
    }

    @Test
    void create_invalidPayload_returns400() {
        Map<String, Object> payload = Map.of("year", 2000, "isbn", "x");
        ResponseEntity<Map<String, String>> resp = rest.exchange(
                "/books", HttpMethod.POST, new HttpEntity<>(payload),
                new ParameterizedTypeReference<>() {});
        assertThat(resp.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        assertThat(resp.getBody()).containsKeys("title", "author");
    }

    @Test
    void list_supportsAuthorFilter() {
        post(Map.of("title", "Book A", "author", "Alice"));
        post(Map.of("title", "Book B", "author", "Bob"));

        ResponseEntity<List<Map<String, Object>>> filtered = rest.exchange(
                "/books?author=Alice", HttpMethod.GET, null, LIST);
        assertThat(filtered.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(filtered.getBody()).hasSize(1);
        assertThat(filtered.getBody().get(0).get("author")).isEqualTo("Alice");
    }

    private void post(Map<String, Object> payload) {
        rest.exchange("/books", HttpMethod.POST, new HttpEntity<>(payload), MAP);
    }
}
