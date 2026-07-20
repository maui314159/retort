package com.example.books;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Integration tests: run the real server on an ephemeral port backed by an
 * in-memory SQLite database and exercise every endpoint over HTTP.
 * Tests are order-independent — each uses unique data.
 */
class BookApiServerTest {

    private static final ObjectMapper mapper = new ObjectMapper();

    private static BookRepository repository;
    private static BookApiServer server;
    private static String baseUrl;

    private final HttpClient client = HttpClient.newHttpClient();

    @BeforeAll
    static void startServer() throws Exception {
        repository = new BookRepository("jdbc:sqlite::memory:");
        server = new BookApiServer(0, repository);
        server.start();
        baseUrl = "http://localhost:" + server.getPort();
    }

    @AfterAll
    static void stopServer() throws Exception {
        server.stop();
        repository.close();
    }

    @Test
    void healthCheckReturnsOk() throws Exception {
        HttpResponse<String> res = get("/health");
        assertEquals(200, res.statusCode());
        assertEquals("ok", mapper.readTree(res.body()).get("status").asText());
    }

    @Test
    void createAndFetchBook() throws Exception {
        String isbn = "isbn-" + UUID.randomUUID();
        HttpResponse<String> created = post("/books", Map.of(
                "title", "Clean Code",
                "author", "Robert C. Martin",
                "year", 2008,
                "isbn", isbn));
        assertEquals(201, created.statusCode());

        JsonNode createdBook = mapper.readTree(created.body());
        int id = createdBook.get("id").asInt();
        assertTrue(id > 0);
        assertEquals("Clean Code", createdBook.get("title").asText());

        HttpResponse<String> fetched = get("/books/" + id);
        assertEquals(200, fetched.statusCode());
        JsonNode book = mapper.readTree(fetched.body());
        assertEquals("Robert C. Martin", book.get("author").asText());
        assertEquals(2008, book.get("year").asInt());
        assertEquals(isbn, book.get("isbn").asText());
    }

    @Test
    void createBookWithoutTitleIsRejected() throws Exception {
        HttpResponse<String> res = post("/books", Map.of("author", "Someone"));
        assertEquals(400, res.statusCode());
        assertTrue(mapper.readTree(res.body()).has("error"));
    }

    @Test
    void createBookWithoutAuthorIsRejected() throws Exception {
        HttpResponse<String> res = post("/books", Map.of("title", "No Author Book"));
        assertEquals(400, res.statusCode());
    }

    @Test
    void listBooksFiltersByAuthor() throws Exception {
        String author = "Author-" + UUID.randomUUID();
        assertEquals(201, post("/books", Map.of("title", "One", "author", author)).statusCode());
        assertEquals(201, post("/books", Map.of("title", "Two", "author", author)).statusCode());
        assertEquals(201, post("/books", Map.of("title", "Three", "author", "Other-" + UUID.randomUUID())).statusCode());

        HttpResponse<String> res = get("/books?author=" + URLEncoder.encode(author, StandardCharsets.UTF_8));
        assertEquals(200, res.statusCode());
        JsonNode books = mapper.readTree(res.body());
        assertEquals(2, books.size());
        books.forEach(b -> assertEquals(author, b.get("author").asText()));
    }

    @Test
    void updateAndDeleteBook() throws Exception {
        HttpResponse<String> created = post("/books", Map.of("title", "Old Title", "author", "A"));
        int id = mapper.readTree(created.body()).get("id").asInt();

        HttpResponse<String> updated = put("/books/" + id,
                Map.of("title", "New Title", "author", "A", "year", 2020, "isbn", "x"));
        assertEquals(200, updated.statusCode());
        assertEquals("New Title", mapper.readTree(updated.body()).get("title").asText());

        HttpResponse<String> deleted = delete("/books/" + id);
        assertEquals(204, deleted.statusCode());

        assertEquals(404, get("/books/" + id).statusCode());
    }

    @Test
    void getMissingBookReturns404() throws Exception {
        assertEquals(404, get("/books/99999999").statusCode());
    }

    private HttpResponse<String> get(String path) throws Exception {
        HttpRequest req = HttpRequest.newBuilder(URI.create(baseUrl + path)).GET().build();
        return client.send(req, HttpResponse.BodyHandlers.ofString());
    }

    private HttpResponse<String> post(String path, Object body) throws Exception {
        return send("POST", path, body);
    }

    private HttpResponse<String> put(String path, Object body) throws Exception {
        return send("PUT", path, body);
    }

    private HttpResponse<String> delete(String path) throws Exception {
        HttpRequest req = HttpRequest.newBuilder(URI.create(baseUrl + path)).DELETE().build();
        return client.send(req, HttpResponse.BodyHandlers.ofString());
    }

    private HttpResponse<String> send(String method, String path, Object body) throws Exception {
        HttpRequest req = HttpRequest.newBuilder(URI.create(baseUrl + path))
                .method(method, HttpRequest.BodyPublishers.ofString(mapper.writeValueAsString(body)))
                .header("Content-Type", "application/json")
                .build();
        return client.send(req, HttpResponse.BodyHandlers.ofString());
    }
}
