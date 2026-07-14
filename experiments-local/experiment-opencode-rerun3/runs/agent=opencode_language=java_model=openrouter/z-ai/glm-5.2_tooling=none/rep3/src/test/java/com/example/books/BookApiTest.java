package com.example.books;

import com.fasterxml.jackson.databind.JsonNode;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class BookApiTest {

    private HttpServer server;
    private TestClient client;
    private Path dbFile;

    @BeforeEach
    void setUp() throws IOException {
        dbFile = Files.createTempFile("books-test-", ".db");
        server = Main.start(0, dbFile.toString());
        client = new TestClient(server.getAddress().getPort());
    }

    @AfterEach
    void tearDown() {
        server.stop(0);
        try {
            Files.deleteIfExists(dbFile);
        } catch (IOException e) {
            // ignore
        }
    }

    @Test
    void healthReturnsOk() throws Exception {
        TestClient.Response r = client.get("/health");
        assertEquals(200, r.status);
        JsonNode node = JsonUtil.mapper().readTree(r.body);
        assertEquals("ok", node.get("status").asText());
    }

    @Test
    void createListGetUpdateDeleteFlow() throws Exception {
        // Create
        String payload = "{\"title\":\"Dune\",\"author\":\"Frank Herbert\",\"year\":1965,\"isbn\":\"9780441172719\"}";
        TestClient.Response created = client.post("/books", payload);
        assertEquals(201, created.status);
        JsonNode createdNode = JsonUtil.mapper().readTree(created.body);
        long id = createdNode.get("id").asLong();
        assertEquals("Dune", createdNode.get("title").asText());

        // List
        TestClient.Response listed = client.get("/books");
        assertEquals(200, listed.status);
        JsonNode listNode = JsonUtil.mapper().readTree(listed.body);
        assertTrue(listNode.isArray());
        assertEquals(1, listNode.size());

        // Get by id
        TestClient.Response fetched = client.get("/books/" + id);
        assertEquals(200, fetched.status);
        assertEquals("Dune", JsonUtil.mapper().readTree(fetched.body).get("title").asText());

        // Update
        String updatePayload = "{\"title\":\"Dune Messiah\",\"author\":\"Frank Herbert\",\"year\":1969,\"isbn\":\"9780441172719\"}";
        TestClient.Response updated = client.put("/books/" + id, updatePayload);
        assertEquals(200, updated.status);
        assertEquals("Dune Messiah", JsonUtil.mapper().readTree(updated.body).get("title").asText());

        // Delete
        TestClient.Response deleted = client.delete("/books/" + id);
        assertEquals(204, deleted.status);

        // Get after delete -> 404
        TestClient.Response afterDelete = client.get("/books/" + id);
        assertEquals(404, afterDelete.status);
    }

    @Test
    void authorFilterWorks() throws Exception {
        client.post("/books", "{\"title\":\"Book A\",\"author\":\"Alice\",\"year\":2001}");
        client.post("/books", "{\"title\":\"Book B\",\"author\":\"Bob\",\"year\":2002}");
        client.post("/books", "{\"title\":\"Book C\",\"author\":\"Alice\",\"year\":2003}");

        TestClient.Response filtered = client.get("/books?author=Alice");
        assertEquals(200, filtered.status);
        JsonNode arr = JsonUtil.mapper().readTree(filtered.body);
        assertEquals(2, arr.size());
        for (JsonNode n : arr) {
            assertEquals("Alice", n.get("author").asText());
        }

        TestClient.Response all = client.get("/books");
        assertEquals(3, JsonUtil.mapper().readTree(all.body).size());
    }

    @Test
    void validationRejectsMissingTitle() throws Exception {
        TestClient.Response r = client.post("/books", "{\"author\":\"Someone\",\"year\":2000}");
        assertEquals(400, r.status);
        JsonNode node = JsonUtil.mapper().readTree(r.body);
        assertNotNull(node.get("error").asText());
        assertTrue(node.get("error").asText().toLowerCase().contains("title"));
    }

    @Test
    void validationRejectsMissingAuthor() throws Exception {
        TestClient.Response r = client.post("/books", "{\"title\":\"Something\",\"year\":2000}");
        assertEquals(400, r.status);
        JsonNode node = JsonUtil.mapper().readTree(r.body);
        assertTrue(node.get("error").asText().toLowerCase().contains("author"));
    }

    @Test
    void getUnknownReturns404() throws Exception {
        TestClient.Response r = client.get("/books/999999");
        assertEquals(404, r.status);
    }
}
