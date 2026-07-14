package com.example.books;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.javalin.Javalin;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class BookApiIntegrationTest {

    private Javalin app;
    private String baseUrl;
    private OkHttpClient client;
    private final ObjectMapper mapper = new ObjectMapper();
    private final MediaType JSON = MediaType.get("application/json; charset=utf-8");
    private Path dbPath;

    @BeforeEach
    void setUp() throws Exception {
        dbPath = Files.createTempFile("books-test-", ".db");
        app = Main.createApp(dbPath.toString());
        app.start(0);
        baseUrl = "http://localhost:" + app.port();
        client = new OkHttpClient.Builder()
                .callTimeout(Duration.ofSeconds(10))
                .build();
    }

    @AfterEach
    void tearDown() {
        if (app != null) {
            app.stop();
        }
        if (dbPath != null) {
            new File(dbPath.toString()).delete();
        }
    }

    private Response post(String path, String json) throws Exception {
        RequestBody body = RequestBody.create(json, JSON);
        Request req = new Request.Builder().url(baseUrl + path).post(body).build();
        return client.newCall(req).execute();
    }

    private Response put(String path, String json) throws Exception {
        RequestBody body = RequestBody.create(json, JSON);
        Request req = new Request.Builder().url(baseUrl + path).put(body).build();
        return client.newCall(req).execute();
    }

    private Response get(String path) throws Exception {
        Request req = new Request.Builder().url(baseUrl + path).get().build();
        return client.newCall(req).execute();
    }

    private Response delete(String path) throws Exception {
        Request req = new Request.Builder().url(baseUrl + path).delete().build();
        return client.newCall(req).execute();
    }

    private String bookJson(String title, String author, Integer year, String isbn) throws Exception {
        var node = mapper.createObjectNode();
        if (title != null) node.put("title", title);
        if (author != null) node.put("author", author);
        if (year != null) node.put("year", year);
        if (isbn != null) node.put("isbn", isbn);
        return mapper.writeValueAsString(node);
    }

    @Test
    void healthCheckReturnsOk() throws Exception {
        try (Response res = get("/health")) {
            assertEquals(200, res.code());
            JsonNode body = mapper.readTree(res.body().string());
            assertEquals("ok", body.get("status").asText());
        }
    }

    @Test
    void createBookPersistsAndReturnsCreated() throws Exception {
        String payload = bookJson("The Hobbit", "J.R.R. Tolkien", 1937, "9780261102217");
        Long id;
        try (Response res = post("/books", payload)) {
            assertEquals(201, res.code());
            JsonNode body = mapper.readTree(res.body().string());
            assertTrue(body.get("id").asLong() > 0);
            assertEquals("The Hobbit", body.get("title").asText());
            assertEquals("J.R.R. Tolkien", body.get("author").asText());
            assertEquals(1937, body.get("year").asInt());
            assertEquals("9780261102217", body.get("isbn").asText());
            id = body.get("id").asLong();
        }
        try (Response res = get("/books/" + id)) {
            assertEquals(200, res.code());
            JsonNode body = mapper.readTree(res.body().string());
            assertEquals(id, body.get("id").asLong());
            assertEquals("The Hobbit", body.get("title").asText());
        }
    }

    @Test
    void createRejectsMissingTitleAndAuthor() throws Exception {
        try (Response res = post("/books", bookJson(null, null, 2020, "x"))) {
            assertEquals(400, res.code());
            JsonNode body = mapper.readTree(res.body().string());
            assertNotNull(body.get("error").asText());
        }
    }

    @Test
    void listSupportsAuthorFilter() throws Exception {
        post("/books", bookJson("Book A", "Alice", 2001, "a"));
        post("/books", bookJson("Book B", "Bob", 2002, "b"));
        post("/books", bookJson("Book C", "Alice", 2003, "c"));

        try (Response res = get("/books?author=Alice")) {
            assertEquals(200, res.code());
            JsonNode body = mapper.readTree(res.body().string());
            assertEquals(2, body.size());
            for (JsonNode node : body) {
                assertEquals("Alice", node.get("author").asText());
            }
        }
        try (Response res = get("/books")) {
            JsonNode body = mapper.readTree(res.body().string());
            assertEquals(3, body.size());
        }
    }

    @Test
    void updateAndDeleteBook() throws Exception {
        Long id;
        try (Response res = post("/books", bookJson("Old Title", "Old Author", 1990, "old"))) {
            id = mapper.readTree(res.body().string()).get("id").asLong();
        }
        try (Response res = put("/books/" + id, bookJson("New Title", "New Author", 2020, "new"))) {
            assertEquals(200, res.code());
            JsonNode body = mapper.readTree(res.body().string());
            assertEquals("New Title", body.get("title").asText());
            assertEquals("New Author", body.get("author").asText());
        }
        try (Response res = get("/books/" + id)) {
            JsonNode body = mapper.readTree(res.body().string());
            assertEquals("New Title", body.get("title").asText());
        }
        try (Response res = delete("/books/" + id)) {
            assertEquals(204, res.code());
        }
        try (Response res = get("/books/" + id)) {
            assertEquals(404, res.code());
        }
    }

    @Test
    void getUnknownBookReturns404() throws Exception {
        try (Response res = get("/books/999999")) {
            assertEquals(404, res.code());
        }
    }
}
