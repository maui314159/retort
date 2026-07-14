package com.example;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.sql.SQLException;
import java.time.Duration;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class BookApiIT {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private Router router;
    private BookService service;
    private HttpClient client;
    private String base;

    @BeforeEach
    void setUp() throws IOException, SQLException {
        service = new BookService("jdbc:sqlite::memory:");
        router = new Router(service, 0);
        router.start();
        base = "http://localhost:" + router.port();
        client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(2)).build();
    }

    @AfterEach
    void tearDown() {
        router.close();
    }

    @Test
    void healthEndpointReturnsUp() throws Exception {
        HttpResponse<String> res = client.send(
                HttpRequest.newBuilder(URI.create(base + "/health")).GET().build(),
                HttpResponse.BodyHandlers.ofString());
        assertEquals(200, res.statusCode());
        assertEquals("application/json", res.headers().firstValue("content-type").orElse(""));
        assertTrue(res.body().contains("\"status\":\"up\""));
    }

    @Test
    void fullBookLifecycle() throws Exception {
        Book book = new Book(null, "The Pragmatic Programmer", "Hunt & Thomas", 1999, "978-0201616224");
        HttpResponse<String> create = post("/books", MAPPER.writeValueAsString(book));
        assertEquals(201, create.statusCode());
        Book created = MAPPER.readValue(create.body(), Book.class);
        assertNotNull(created.getId());
        assertEquals("The Pragmatic Programmer", created.getTitle());

        HttpResponse<String> get = get("/books/" + created.getId());
        assertEquals(200, get.statusCode());
        assertEquals(created.getId(), MAPPER.readValue(get.body(), Book.class).getId());

        Book update = new Book(null, "Pragmatic Programmer, The", "Hunt & Thomas", 1999, "978-0201616224");
        HttpResponse<String> putRes = put("/books/" + created.getId(), MAPPER.writeValueAsString(update));
        assertEquals(200, putRes.statusCode());
        assertEquals("Pragmatic Programmer, The", MAPPER.readValue(putRes.body(), Book.class).getTitle());

        HttpResponse<String> del = delete("/books/" + created.getId());
        assertEquals(204, del.statusCode());

        HttpResponse<String> after = get("/books/" + created.getId());
        assertEquals(404, after.statusCode());
    }

    @Test
    void listSupportsAuthorFilter() throws Exception {
        post("/books", MAPPER.writeValueAsString(new Book(null, "A", "Alice", 2001, "i1")));
        post("/books", MAPPER.writeValueAsString(new Book(null, "B", "Bob", 2002, "i2")));
        post("/books", MAPPER.writeValueAsString(new Book(null, "C", "Alice", 2003, "i3")));

        HttpResponse<String> all = get("/books");
        assertEquals(200, all.statusCode());
        List<?> list = MAPPER.readValue(all.body(), List.class);
        assertEquals(3, list.size());

        HttpResponse<String> filtered = get("/books?author=Alice");
        List<?> alice = MAPPER.readValue(filtered.body(), List.class);
        assertEquals(2, alice.size());
        assertTrue(((Map<?, ?>) alice.get(0)).get("author").toString().contains("Alice"));
    }

    @Test
    void createRejectsInvalidInput() throws Exception {
        Book bad = new Book(null, null, "Alice", 2000, null);
        HttpResponse<String> res = post("/books", MAPPER.writeValueAsString(bad));
        assertEquals(400, res.statusCode());
        assertTrue(res.body().contains("title"));
    }

    @Test
    void updateNonExistentReturns404() throws Exception {
        Book book = new Book(null, "T", "A", 2000, "x");
        HttpResponse<String> res = put("/books/9999", MAPPER.writeValueAsString(book));
        assertEquals(404, res.statusCode());
    }

    private HttpResponse<String> get(String path) throws Exception {
        return client.send(HttpRequest.newBuilder(URI.create(base + path)).GET().build(),
                HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
    }

    private HttpResponse<String> post(String path, String body) throws Exception {
        return client.send(HttpRequest.newBuilder(URI.create(base + path))
                .POST(HttpRequest.BodyPublishers.ofString(body))
                .header("Content-Type", "application/json")
                .build(), HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
    }

    private HttpResponse<String> put(String path, String body) throws Exception {
        return client.send(HttpRequest.newBuilder(URI.create(base + path))
                .PUT(HttpRequest.BodyPublishers.ofString(body))
                .header("Content-Type", "application/json")
                .build(), HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
    }

    private HttpResponse<String> delete(String path) throws Exception {
        return client.send(HttpRequest.newBuilder(URI.create(base + path)).DELETE().build(),
                HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
    }
}
