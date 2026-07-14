package com.example.books;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import io.javalin.Javalin;
import io.javalin.testtools.JavalinTest;
import okhttp3.Response;

/**
 * End-to-end HTTP tests that drive the full Javalin app with a real
 * SQLite file backing it. Each test gets a fresh tempfile so cases
 * cannot leak state.
 */
class BookApiTest {

    private static final ObjectMapper MAPPER = new com.fasterxml.jackson.databind.ObjectMapper();

    private Javalin app;
    private Path tmpFile;

    @BeforeEach
    void setUp() throws Exception {
        tmpFile = Files.createTempFile("books-api-test-", ".db");
        tmpFile.toFile().deleteOnExit();
        // Wipe whatever initializeSchema wrote so each test starts clean.
        Files.deleteIfExists(tmpFile);
        app = Application.bootstrap("jdbc:sqlite:" + tmpFile);
    }

    @Test
    @DisplayName("GET /health returns 200 with status:ok")
    void healthCheck() {
        JavalinTest.test(app, (jav, http) -> {
            Response res = http.get("/health");
            assertEquals(200, res.code());
            Map<?, ?> body = MAPPER.readValue(res.body().bytes(), Map.class);
            assertEquals("ok", body.get("status"));
        });
    }

    @Test
    @DisplayName("full CRUD lifecycle: create, read, list, update, delete")
    void fullCrudLifecycle() throws IOException {
        JavalinTest.test(app, (jav, http) -> {
            // 1. Create
            Response created = http.post("/books", Map.of(
                    "title", "Dune",
                    "author", "Frank Herbert",
                    "year", 1965,
                    "isbn", "978-0441172719"));
            assertEquals(201, created.code());
            Book saved = MAPPER.readValue(created.body().bytes(), Book.class);
            assertNotNull(saved.getId());
            assertEquals("Dune", saved.getTitle());

            long id = saved.getId();

            // 2. Read by id
            Response got = http.get("/books/" + id);
            assertEquals(200, got.code());
            Book fetched = MAPPER.readValue(got.body().bytes(), Book.class);
            assertEquals("Dune", fetched.getTitle());
            assertEquals(1965, fetched.getYear());

            // 3. List
            Response list = http.get("/books");
            assertEquals(200, list.code());
            List<Book> books = MAPPER.readValue(list.body().bytes(), new TypeReference<List<Book>>() {});
            assertEquals(1, books.size());

            // 4. Update
            Response updated = http.put("/books/" + id, Map.of(
                    "title", "Dune (Revised)",
                    "author", "Frank Herbert",
                    "year", 1990,
                    "isbn", "978-0441172719"));
            assertEquals(200, updated.code());
            Book after = MAPPER.readValue(updated.body().bytes(), Book.class);
            assertEquals("Dune (Revised)", after.getTitle());
            assertEquals(1990, after.getYear());

            // 5. Delete
            Response deleted = http.delete("/books/" + id);
            assertEquals(204, deleted.code());

            // 6. Confirm gone
            Response missing = http.get("/books/" + id);
            assertEquals(404, missing.code());
        });
    }

    @Test
    @DisplayName("POST /books rejects missing title with 400 and a stable error envelope")
    void createRejectsMissingTitle() {
        JavalinTest.test(app, (jav, http) -> {
            Response res = http.post("/books", Map.of(
                    "author", "Anonymous"));
            assertEquals(400, res.code());
            Map<?, ?> body = MAPPER.readValue(res.body().bytes(), Map.class);
            assertEquals("validation_failed", body.get("error"));
            assertTrue(((String) body.get("message")).contains("title"));
        });
    }

    @Test
    @DisplayName("GET /books?author= filters case-insensitively")
    void authorFilter() {
        JavalinTest.test(app, (jav, http) -> {
            http.post("/books", Map.of("title", "A", "author", "Tolkien"));
            http.post("/books", Map.of("title", "B", "author", "tolkien"));
            http.post("/books", Map.of("title", "C", "author", "Rowling"));

            Response res = http.get("/books?author=TOLKIEN");
            assertEquals(200, res.code());
            List<Book> books = MAPPER.readValue(res.body().bytes(), new TypeReference<List<Book>>() {});
            assertEquals(2, books.size());
        });
    }

    @Test
    @DisplayName("GET /books/{id} for an unknown id returns 404 with not_found envelope")
    void getUnknownReturnsNotFound() {
        JavalinTest.test(app, (jav, http) -> {
            Response res = http.get("/books/9999");
            assertEquals(404, res.code());
            Map<?, ?> body = MAPPER.readValue(res.body().bytes(), Map.class);
            assertEquals("not_found", body.get("error"));
        });
    }
    void updateWithInvalidId() {
        JavalinTest.test(app, (jav, http) -> {
            Response res = http.put("/books/notanumber", Map.of(
                    "title", "x", "author", "y"));
            assertEquals(400, res.code());
            Map<?, ?> body = MAPPER.readValue(res.body().bytes(), Map.class);
            assertEquals("validation_failed", body.get("error"));
        });
    }

    @Test
    @DisplayName("Unknown routes return a 404 with a JSON error envelope")
    void unknownRouteReturns404() throws IOException {
        JavalinTest.test(app, (jav, http) -> {
            Response res = http.get("/no/such/path");
            assertEquals(404, res.code());
            Map<?, ?> body = MAPPER.readValue(res.body().bytes(), Map.class);
            // Javalin synthesizes a 404 via HttpResponseException; we just
            // assert the envelope is JSON with a non-blank message.
            String message = (String) body.get("message");
            assertNotNull(message, "missing message");
            assertTrue(message != null && !message.isBlank(), "message should be non-blank");
        });
    }
}
