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
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class BookApiTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private Javalin app;
    private HttpClient client;
    private String base;

    @BeforeEach
    void setUp() {
        BookRepository repo = new BookRepository("jdbc:sqlite::memory:");
        app = new BookController(repo).createApp();
        app.start(0);
        int port = app.port();
        base = "http://localhost:" + port;
        client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(2)).build();
    }

    @AfterEach
    void tearDown() {
        app.stop();
    }

    @Test
    void healthReturnsOk() throws Exception {
        HttpResponse<String> res = send("GET", "/health", null);
        assertEquals(200, res.statusCode());
        JsonNode body = MAPPER.readTree(res.body());
        assertEquals("ok", body.get("status").asText());
    }

    @Test
    void fullCrudLifecycleRoundTripsThroughHttp() throws Exception {
        // POST /books -> 201
        String payload = "{\"title\":\"Dune\",\"author\":\"Frank Herbert\","
                + "\"year\":1965,\"isbn\":\"0441172717\"}";
        HttpResponse<String> createRes = send("POST", "/books", payload);
        assertEquals(201, createRes.statusCode());
        JsonNode created = MAPPER.readTree(createRes.body());
        long id = created.get("id").asLong();
        assertTrue(id > 0);
        assertEquals("Dune", created.get("title").asText());
        assertEquals("Frank Herbert", created.get("author").asText());

        // GET /books/{id}
        HttpResponse<String> getRes = send("GET", "/books/" + id, null);
        assertEquals(200, getRes.statusCode());
        assertEquals(id, MAPPER.readTree(getRes.body()).get("id").asLong());

        // GET /books -> array containing the new book
        HttpResponse<String> listRes = send("GET", "/books", null);
        assertEquals(200, listRes.statusCode());
        JsonNode list = MAPPER.readTree(listRes.body());
        assertTrue(list.isArray());
        assertEquals(1, list.size());

        // PUT /books/{id}
        String update = "{\"title\":\"Dune (2nd ed.)\",\"author\":\"Frank Herbert\","
                + "\"year\":1965,\"isbn\":\"0441172717\"}";
        HttpResponse<String> putRes = send("PUT", "/books/" + id, update);
        assertEquals(200, putRes.statusCode());
        assertEquals("Dune (2nd ed.)", MAPPER.readTree(putRes.body()).get("title").asText());

        // DELETE /books/{id}
        HttpResponse<String> delRes = send("DELETE", "/books/" + id, null);
        assertEquals(204, delRes.statusCode());

        // GET /books/{id} -> 404
        HttpResponse<String> afterDel = send("GET", "/books/" + id, null);
        assertEquals(404, afterDel.statusCode());
    }

    @Test
    void listFiltersByAuthorQueryParam() throws Exception {
        send("POST", "/books", bookJson("Dune", "Frank Herbert", 1965, "1"));
        send("POST", "/books", bookJson("Foundation", "Isaac Asimov", 1951, "2"));
        send("POST", "/books", bookJson("Children of Dune", "Frank Herbert", 1976, "3"));

        HttpResponse<String> frank = send("GET", "/books?author=Frank+Herbert", null);
        assertEquals(200, frank.statusCode());
        JsonNode body = MAPPER.readTree(frank.body());
        assertEquals(2, body.size());
        for (JsonNode node : body) {
            assertEquals("Frank Herbert", node.get("author").asText());
        }

        HttpResponse<String> asimov = send("GET", "/books?author=Isaac+Asimov", null);
        assertEquals(200, asimov.statusCode());
        assertEquals(1, MAPPER.readTree(asimov.body()).size());

        HttpResponse<String> none = send("GET", "/books?author=Nobody", null);
        assertEquals(200, none.statusCode());
        assertEquals(0, MAPPER.readTree(none.body()).size());
    }

    @Test
    void createAssignsSequentialIds() throws Exception {
        HttpResponse<String> r1 = send("POST", "/books", bookJson("A", "Alice", 2000, null));
        HttpResponse<String> r2 = send("POST", "/books", bookJson("B", "Bob", 2001, null));
        long id1 = MAPPER.readTree(r1.body()).get("id").asLong();
        long id2 = MAPPER.readTree(r2.body()).get("id").asLong();
        assertNotEquals(id1, id2);
    }

    private static String bookJson(String title, String author, Integer year, String isbn) {
        StringBuilder sb = new StringBuilder();
        sb.append("{\"title\":\"").append(title).append("\",");
        sb.append("\"author\":\"").append(author).append("\"");
        if (year != null) sb.append(",\"year\":").append(year);
        if (isbn != null) sb.append(",\"isbn\":\"").append(isbn).append("\"");
        sb.append("}");
        return sb.toString();
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
