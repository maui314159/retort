package com.books;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Integration tests that boot the real server on an ephemeral port backed by
 * a throwaway SQLite file, and exercise the API over HTTP.
 */
class BookApiTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private BookServer server;
    private HttpClient client;
    private String base;
    private Path dbFile;

    @BeforeEach
    void setUp() throws Exception {
        dbFile = Files.createTempFile("books-test-", ".db");
        Files.deleteIfExists(dbFile); // let SQLite create a fresh file
        server = new BookServer(0, dbFile.toString());
        server.start();
        base = "http://localhost:" + server.getPort();
        client = HttpClient.newHttpClient();
    }

    @AfterEach
    void tearDown() throws Exception {
        server.stop();
        Files.deleteIfExists(dbFile);
    }

    @Test
    void healthCheckReturnsOk() throws Exception {
        HttpResponse<String> response = client.send(
                HttpRequest.newBuilder(URI.create(base + "/health")).GET().build(),
                HttpResponse.BodyHandlers.ofString());

        assertEquals(200, response.statusCode());
        assertEquals("ok", MAPPER.readTree(response.body()).get("status").asText());
    }

    @Test
    void createBookThenGetById() throws Exception {
        HttpResponse<String> created = postJson("/books",
                "{\"title\":\"Dune\",\"author\":\"Frank Herbert\",\"year\":1965,\"isbn\":\"9780441172719\"}");
        assertEquals(201, created.statusCode());

        JsonNode book = MAPPER.readTree(created.body());
        long id = book.get("id").asLong();
        assertEquals("Dune", book.get("title").asText());
        assertEquals("Frank Herbert", book.get("author").asText());
        assertEquals(1965, book.get("year").asInt());

        HttpResponse<String> fetched = client.send(
                HttpRequest.newBuilder(URI.create(base + "/books/" + id)).GET().build(),
                HttpResponse.BodyHandlers.ofString());
        assertEquals(200, fetched.statusCode());
        assertEquals("Dune", MAPPER.readTree(fetched.body()).get("title").asText());
    }

    @Test
    void createBookWithoutTitleOrAuthorIsRejected() throws Exception {
        HttpResponse<String> noTitle = postJson("/books", "{\"author\":\"Someone\"}");
        assertEquals(400, noTitle.statusCode());
        assertTrue(noTitle.body().contains("title and author are required"));

        HttpResponse<String> noAuthor = postJson("/books", "{\"title\":\"Untitled\"}");
        assertEquals(400, noAuthor.statusCode());

        HttpResponse<String> invalidJson = postJson("/books", "not json");
        assertEquals(400, invalidJson.statusCode());
    }

    @Test
    void listBooksWithAuthorFilter() throws Exception {
        postJson("/books", "{\"title\":\"Dune\",\"author\":\"Frank Herbert\"}");
        postJson("/books", "{\"title\":\"Children of Dune\",\"author\":\"Frank Herbert\"}");
        postJson("/books", "{\"title\":\"The Hobbit\",\"author\":\"J.R.R. Tolkien\"}");

        HttpResponse<String> all = client.send(
                HttpRequest.newBuilder(URI.create(base + "/books")).GET().build(),
                HttpResponse.BodyHandlers.ofString());
        assertEquals(200, all.statusCode());
        assertEquals(3, MAPPER.readTree(all.body()).size());

        HttpResponse<String> filtered = client.send(
                HttpRequest.newBuilder(URI.create(base + "/books?author=Frank%20Herbert")).GET().build(),
                HttpResponse.BodyHandlers.ofString());
        assertEquals(200, filtered.statusCode());
        JsonNode books = MAPPER.readTree(filtered.body());
        assertEquals(2, books.size());
        for (JsonNode book : books) {
            assertEquals("Frank Herbert", book.get("author").asText());
        }
    }

    @Test
    void updateAndDeleteBook() throws Exception {
        HttpResponse<String> created = postJson("/books", "{\"title\":\"Old Title\",\"author\":\"An Author\"}");
        long id = MAPPER.readTree(created.body()).get("id").asLong();

        HttpResponse<String> updated = putJson("/books/" + id,
                "{\"title\":\"New Title\",\"author\":\"An Author\",\"year\":2001}");
        assertEquals(200, updated.statusCode());
        assertEquals("New Title", MAPPER.readTree(updated.body()).get("title").asText());

        HttpResponse<String> deleted = client.send(
                HttpRequest.newBuilder(URI.create(base + "/books/" + id)).DELETE().build(),
                HttpResponse.BodyHandlers.ofString());
        assertEquals(204, deleted.statusCode());

        HttpResponse<String> afterDelete = client.send(
                HttpRequest.newBuilder(URI.create(base + "/books/" + id)).GET().build(),
                HttpResponse.BodyHandlers.ofString());
        assertEquals(404, afterDelete.statusCode());
    }

    @Test
    void unknownIdReturns404() throws Exception {
        HttpResponse<String> get = client.send(
                HttpRequest.newBuilder(URI.create(base + "/books/9999")).GET().build(),
                HttpResponse.BodyHandlers.ofString());
        assertEquals(404, get.statusCode());

        HttpResponse<String> put = putJson("/books/9999", "{\"title\":\"T\",\"author\":\"A\"}");
        assertEquals(404, put.statusCode());

        HttpResponse<String> delete = client.send(
                HttpRequest.newBuilder(URI.create(base + "/books/9999")).DELETE().build(),
                HttpResponse.BodyHandlers.ofString());
        assertEquals(404, delete.statusCode());
    }

    private HttpResponse<String> postJson(String path, String json) throws Exception {
        return client.send(
                HttpRequest.newBuilder(URI.create(base + path))
                        .header("Content-Type", "application/json")
                        .POST(HttpRequest.BodyPublishers.ofString(json))
                        .build(),
                HttpResponse.BodyHandlers.ofString());
    }

    private HttpResponse<String> putJson(String path, String json) throws Exception {
        return client.send(
                HttpRequest.newBuilder(URI.create(base + path))
                        .header("Content-Type", "application/json")
                        .PUT(HttpRequest.BodyPublishers.ofString(json))
                        .build(),
                HttpResponse.BodyHandlers.ofString());
    }
}
