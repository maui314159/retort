package com.example.books;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.javalin.Javalin;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class BookApiValidationTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private Javalin app;
    private HttpClient client;
    private String base;

    @BeforeEach
    void setUp() {
        BookRepository repo = new BookRepository("jdbc:sqlite::memory:");
        app = new BookController(repo).createApp();
        app.start(0);
        base = "http://localhost:" + app.port();
        client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(2)).build();
    }

    @AfterEach
    void tearDown() {
        app.stop();
    }

    @Test
    void createWithoutTitleReturns400() throws Exception {
        HttpResponse<String> res = send("POST", "/books",
                "{\"author\":\"Frank Herbert\",\"year\":1965}");
        assertEquals(400, res.statusCode());
        JsonNode body = MAPPER.readTree(res.body());
        assertTrue(body.has("details"));
        boolean foundTitleError = false;
        for (JsonNode d : body.get("details")) {
            if (d.asText().toLowerCase().contains("title")) {
                foundTitleError = true;
            }
        }
        assertTrue(foundTitleError, "expected a title-required error in " + body);
    }

    @Test
    void createWithoutAuthorReturns400() throws Exception {
        HttpResponse<String> res = send("POST", "/books",
                "{\"title\":\"Dune\",\"year\":1965}");
        assertEquals(400, res.statusCode());
        JsonNode body = MAPPER.readTree(res.body());
        boolean foundAuthorError = false;
        for (JsonNode d : body.get("details")) {
            if (d.asText().toLowerCase().contains("author")) {
                foundAuthorError = true;
            }
        }
        assertTrue(foundAuthorError, "expected an author-required error in " + body);
    }

    @Test
    void createWithBlankTitleAndAuthorReturnsBothErrors() throws Exception {
        HttpResponse<String> res = send("POST", "/books",
                "{\"title\":\"   \",\"author\":\"\"}");
        assertEquals(400, res.statusCode());
        JsonNode body = MAPPER.readTree(res.body());
        assertEquals(2, body.get("details").size());
    }

    @Test
    void putOnUnknownIdReturns404() throws Exception {
        HttpResponse<String> res = send("PUT", "/books/9999",
                "{\"title\":\"X\",\"author\":\"Y\"}");
        assertEquals(404, res.statusCode());
    }

    @Test
    void getOnUnknownIdReturns404() throws Exception {
        HttpResponse<String> res = send("GET", "/books/9999", null);
        assertEquals(404, res.statusCode());
    }

    @Test
    void deleteOnUnknownIdReturns404() throws Exception {
        HttpResponse<String> res = send("DELETE", "/books/9999", null);
        assertEquals(404, res.statusCode());
    }

    @Test
    void nonNumericIdReturns400() throws Exception {
        HttpResponse<String> res = send("GET", "/books/notanumber", null);
        assertEquals(400, res.statusCode());
    }

    @Test
    void malformedJsonReturns400() throws Exception {
        HttpResponse<String> res = send("POST", "/books", "{not json");
        assertEquals(400, res.statusCode());
        JsonNode body = MAPPER.readTree(res.body());
        assertTrue(body.has("error"));
    }

    @Test
    void updateValidatesRequiredFields() throws Exception {
        // First create a real book.
        HttpResponse<String> created = send("POST", "/books",
                "{\"title\":\"Dune\",\"author\":\"Frank Herbert\"}");
        long id = MAPPER.readTree(created.body()).get("id").asLong();

        // Now update it with missing title.
        HttpResponse<String> bad = send("PUT", "/books/" + id, "{\"author\":\"X\"}");
        assertEquals(400, bad.statusCode());
    }

    private HttpResponse<String> send(String method, String path, String body) throws Exception {
        HttpRequest.Builder b = HttpRequest.newBuilder()
                .uri(URI.create(base + path))
                .timeout(Duration.ofSeconds(2));
        if (body != null) {
            b.header("Content-Type", "application/json");
            b.method(method, HttpRequest.BodyPublishers.ofString(body));
        } else {
            b.method(method, HttpRequest.BodyPublishers.noBody());
        }
        return client.send(b.build(), HttpResponse.BodyHandlers.ofString());
    }
}
