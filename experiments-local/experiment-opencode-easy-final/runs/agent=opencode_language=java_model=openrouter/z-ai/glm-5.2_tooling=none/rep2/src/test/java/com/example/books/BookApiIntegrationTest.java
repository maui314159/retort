package com.example.books;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.sql.SQLException;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class BookApiIntegrationTest {

    private TestServer server;

    @BeforeEach
    void setUp() throws IOException, SQLException {
        server = new TestServer();
    }

    @AfterEach
    void tearDown() {
        if (server != null) server.close();
    }

    @Test
    void healthReturnsOk() throws IOException, InterruptedException {
        var resp = server.send("GET", "/health", null);
        assertEquals(200, resp.statusCode());
        assertEquals("{\"status\":\"ok\"}", resp.body());
    }

    @Test
    void createListGetUpdateDeleteLifecycle() throws IOException, InterruptedException {
        String payload = "{\"title\":\"Dune\",\"author\":\"Frank Herbert\",\"year\":1965,\"isbn\":\"9780441172719\"}";

        var create = server.send("POST", "/books", payload);
        assertEquals(201, create.statusCode());
        assertTrue(create.body().contains("\"id\":"));
        assertTrue(create.body().contains("\"title\":\"Dune\""));

        var list = server.send("GET", "/books", null);
        assertEquals(200, list.statusCode());
        assertTrue(list.body().startsWith("["));
        assertTrue(list.body().contains("Dune"));

        long id = extractId(create.body());

        var one = server.send("GET", "/books/" + id, null);
        assertEquals(200, one.statusCode());
        assertTrue(one.body().contains("\"author\":\"Frank Herbert\""));

        var update = server.send("PUT", "/books/" + id,
                "{\"title\":\"Dune Updated\",\"author\":\"Frank Herbert\",\"year\":1965,\"isbn\":\"X\"}");
        assertEquals(200, update.statusCode());
        assertTrue(update.body().contains("\"title\":\"Dune Updated\""));

        var del = server.send("DELETE", "/books/" + id, null);
        assertEquals(204, del.statusCode());

        var afterDelete = server.send("GET", "/books/" + id, null);
        assertEquals(404, afterDelete.statusCode());
    }

    @Test
    void authorFilterAndValidationErrors() throws IOException, InterruptedException {
        server.send("POST", "/books", "{\"title\":\"A\",\"author\":\"Alice\",\"year\":2001,\"isbn\":\"i1\"}");
        server.send("POST", "/books", "{\"title\":\"B\",\"author\":\"Bob\",\"year\":2002,\"isbn\":\"i2\"}");

        var filtered = server.send("GET", "/books?author=Alice", null);
        assertEquals(200, filtered.statusCode());
        assertTrue(filtered.body().contains("\"author\":\"Alice\""));
        assertTrue(!filtered.body().contains("\"author\":\"Bob\""));

        var missingTitle = server.send("POST", "/books",
                "{\"author\":\"NoTitle\"}");
        assertEquals(400, missingTitle.statusCode());
        assertTrue(missingTitle.body().contains("title is required"));

        var missingAuthor = server.send("POST", "/books",
                "{\"title\":\"NoAuthor\"}");
        assertEquals(400, missingAuthor.statusCode());
        assertTrue(missingAuthor.body().contains("author is required"));

        var unknown = server.send("GET", "/books/99999", null);
        assertEquals(404, unknown.statusCode());
    }

    private static long extractId(String json) {
        int idx = json.indexOf("\"id\":");
        int start = idx + 5;
        int end = start;
        while (end < json.length() && Character.isDigit(json.charAt(end))) end++;
        return Long.parseLong(json.substring(start, end));
    }
}
