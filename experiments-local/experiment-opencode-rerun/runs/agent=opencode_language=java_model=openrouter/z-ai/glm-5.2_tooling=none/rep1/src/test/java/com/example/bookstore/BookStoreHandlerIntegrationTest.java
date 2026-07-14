package com.example.bookstore;

import com.sun.net.httpserver.HttpServer;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.net.InetSocketAddress;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.sql.SQLException;
import java.time.Duration;
import java.util.concurrent.Executors;

import static org.junit.jupiter.api.Assertions.*;

class BookStoreHandlerIntegrationTest {

    private HttpServer server;
    private int port;
    private HttpClient client;

    @BeforeEach
    void setUp() throws Exception {
        BookDao dao = new BookDao("jdbc:sqlite::memory:");
        dao.init();
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/", new BookStoreHandler(dao));
        server.setExecutor(Executors.newSingleThreadExecutor());
        server.start();
        port = server.getAddress().getPort();

        client = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(2))
                .build();
    }

    @AfterEach
    void tearDown() {
        if (server != null) server.stop(0);
    }

    @Test
    void healthCheckReturnsUp() throws Exception {
        HttpResponse<String> res = get("/health");
        assertEquals(200, res.statusCode());
        assertTrue(res.body().contains("\"status\":\"up\""));
        assertTrue(res.headers().firstValue("Content-Type").orElse("").contains("application/json"));
    }

    @Test
    void createListGetUpdateDeleteRoundTrip() throws Exception {
        // Create
        String body = "{\"title\":\"Refactoring\",\"author\":\"Fowler\",\"year\":1999,\"isbn\":\"978-0201485677\"}";
        HttpResponse<String> post = send("/books", "POST", body);
        assertEquals(201, post.statusCode());
        assertTrue(post.body().contains("\"id\":"));
        assertTrue(post.body().contains("Refactoring"));
        long id = extractId(post.body());

        // List
        HttpResponse<String> list = get("/books");
        assertEquals(200, list.statusCode());
        assertTrue(list.body().startsWith("["), "list should return JSON array");
        assertTrue(list.body().contains("Refactoring"));

        // Filter by author
        HttpResponse<String> filtered = get("/books?author=Fowler");
        assertEquals(200, filtered.statusCode());
        assertTrue(filtered.body().contains("Refactoring"));
        assertFalse(filtered.body().contains("Clean Code"));

        // Get by id
        HttpResponse<String> one = get("/books/" + id);
        assertEquals(200, one.statusCode());
        assertTrue(one.body().contains("\"id\":" + id));

        // Update
        String update = "{\"title\":\"Refactoring (2nd)\",\"author\":\"Fowler & Beck\",\"year\":2018,\"isbn\":\"978-0134757777\"}";
        HttpResponse<String> put = send("/books/" + id, "PUT", update);
        assertEquals(200, put.statusCode());
        assertTrue(put.body().contains("Refactoring (2nd)"));

        // Delete
        HttpResponse<String> del = send("/books/" + id, "DELETE", null);
        assertEquals(204, del.statusCode());
        assertEquals("", del.body());

        // Get now 404
        HttpResponse<String> missing = get("/books/" + id);
        assertEquals(404, missing.statusCode());
    }

    @Test
    void validationErrorsReturn400WithErrorsList() throws Exception {
        HttpResponse<String> bad = send("/books", "POST", "{\"title\":\"\",\"author\":\"\"}");
        assertEquals(400, bad.statusCode());
        assertTrue(bad.body().contains("errors"));
        assertTrue(bad.body().contains("title is required"));
        assertTrue(bad.body().contains("author is required"));
    }

    @Test
    void malformedJsonReturns400() throws Exception {
        HttpResponse<String> bad = send("/books", "POST", "{not json}");
        assertEquals(400, bad.statusCode());
        assertTrue(bad.body().contains("malformed JSON"));
    }

    @Test
    void missingBookReturns404() throws Exception {
        HttpResponse<String> res = get("/books/999999");
        assertEquals(404, res.statusCode());
        assertTrue(res.body().contains("book not found"));
    }

    @Test
    void updateMissingBookReturns404() throws Exception {
        HttpResponse<String> res = send("/books/999999", "PUT",
                "{\"title\":\"X\",\"author\":\"Y\"}");
        assertEquals(404, res.statusCode());
    }

    @Test
    void unknownRouteReturns404() throws Exception {
        HttpResponse<String> res = get("/unknown");
        assertEquals(404, res.statusCode());
    }

    private HttpResponse<String> get(String path) throws Exception {
        return send(path, "GET", null);
    }

    private HttpResponse<String> send(String path, String method, String body) throws Exception {
        HttpRequest.Builder b = HttpRequest.newBuilder()
                .uri(URI.create("http://127.0.0.1:" + port + path))
                .timeout(Duration.ofSeconds(2));
        if (body == null) {
            if ("DELETE".equalsIgnoreCase(method)) b.DELETE();
            else if ("GET".equalsIgnoreCase(method)) b.GET();
            else b.method(method, HttpRequest.BodyPublishers.noBody());
        } else {
            b.header("Content-Type", "application/json")
              .method(method, HttpRequest.BodyPublishers.ofString(body));
        }
        return client.send(b.build(), HttpResponse.BodyHandlers.ofString());
    }

    private long extractId(String json) {
        int i = json.indexOf("\"id\":");
        int j = json.indexOf(",", i);
        if (j == -1) j = json.indexOf("}", i);
        return Long.parseLong(json.substring(i + 5, j).trim());
    }
}
