package com.example.books;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
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
 * Integration tests: boot the server on an ephemeral port backed by a
 * temporary SQLite file and exercise the HTTP API end to end.
 */
class BookApiTest {

    private static final Gson GSON = new Gson();

    private static BookApiServer server;
    private static HttpClient client;
    private static String base;

    @BeforeAll
    static void startServer() throws Exception {
        Path db = Files.createTempFile("books-test", ".db");
        Files.deleteIfExists(db); // let SQLite create it fresh
        server = new BookApiServer(0, BookRepository.forFile(db.toString()));
        server.start();
        base = "http://localhost:" + server.getPort();
        client = HttpClient.newHttpClient();
    }

    @AfterAll
    static void stopServer() {
        server.stop();
    }

    @BeforeEach
    void clearBooks() throws Exception {
        server.getRepo().deleteAll();
    }

    @Test
    void healthReturnsOk() throws Exception {
        HttpResponse<String> res = send("GET", "/health", null);
        assertEquals(200, res.statusCode());
        assertEquals("ok", GSON.fromJson(res.body(), JsonObject.class).get("status").getAsString());
    }

    @Test
    void createAndGetBookById() throws Exception {
        HttpResponse<String> created = send("POST", "/books",
                "{\"title\":\"Dune\",\"author\":\"Frank Herbert\",\"year\":1965,\"isbn\":\"9780441172719\"}");
        assertEquals(201, created.statusCode());
        JsonObject book = GSON.fromJson(created.body(), JsonObject.class);
        long id = book.get("id").getAsLong();
        assertTrue(id > 0);
        assertEquals("Dune", book.get("title").getAsString());

        HttpResponse<String> fetched = send("GET", "/books/" + id, null);
        assertEquals(200, fetched.statusCode());
        JsonObject fetchedBook = GSON.fromJson(fetched.body(), JsonObject.class);
        assertEquals("Frank Herbert", fetchedBook.get("author").getAsString());
        assertEquals(1965, fetchedBook.get("year").getAsInt());
        assertEquals("9780441172719", fetchedBook.get("isbn").getAsString());
    }

    @Test
    void createWithoutRequiredFieldsReturns400() throws Exception {
        HttpResponse<String> missingTitle = send("POST", "/books", "{\"author\":\"Someone\"}");
        assertEquals(400, missingTitle.statusCode());

        HttpResponse<String> missingAuthor = send("POST", "/books", "{\"title\":\"Something\"}");
        assertEquals(400, missingAuthor.statusCode());

        HttpResponse<String> invalidJson = send("POST", "/books", "not json");
        assertEquals(400, invalidJson.statusCode());
    }

    @Test
    void listBooksWithAuthorFilter() throws Exception {
        send("POST", "/books", "{\"title\":\"Dune\",\"author\":\"Frank Herbert\"}");
        send("POST", "/books", "{\"title\":\"Children of Dune\",\"author\":\"Frank Herbert\"}");
        send("POST", "/books", "{\"title\":\"The Left Hand of Darkness\",\"author\":\"Ursula K. Le Guin\"}");

        HttpResponse<String> all = send("GET", "/books", null);
        assertEquals(200, all.statusCode());
        assertEquals(3, GSON.fromJson(all.body(), JsonArray.class).size());

        HttpResponse<String> filtered = send("GET", "/books?author=Frank%20Herbert", null);
        assertEquals(200, filtered.statusCode());
        JsonArray herbert = GSON.fromJson(filtered.body(), JsonArray.class);
        assertEquals(2, herbert.size());
        herbert.forEach(b -> assertEquals("Frank Herbert",
                b.getAsJsonObject().get("author").getAsString()));
    }

    @Test
    void updateBook() throws Exception {
        HttpResponse<String> created = send("POST", "/books",
                "{\"title\":\"Old Title\",\"author\":\"Author\"}");
        long id = GSON.fromJson(created.body(), JsonObject.class).get("id").getAsLong();

        HttpResponse<String> updated = send("PUT", "/books/" + id,
                "{\"title\":\"New Title\",\"author\":\"Author\",\"year\":2001}");
        assertEquals(200, updated.statusCode());
        JsonObject book = GSON.fromJson(updated.body(), JsonObject.class);
        assertEquals("New Title", book.get("title").getAsString());
        assertEquals(2001, book.get("year").getAsInt());

        HttpResponse<String> notFound = send("PUT", "/books/99999",
                "{\"title\":\"X\",\"author\":\"Y\"}");
        assertEquals(404, notFound.statusCode());

        HttpResponse<String> invalid = send("PUT", "/books/" + id, "{\"title\":\"Only Title\"}");
        assertEquals(400, invalid.statusCode());
    }

    @Test
    void deleteBook() throws Exception {
        HttpResponse<String> created = send("POST", "/books",
                "{\"title\":\"To Delete\",\"author\":\"Author\"}");
        long id = GSON.fromJson(created.body(), JsonObject.class).get("id").getAsLong();

        HttpResponse<String> deleted = send("DELETE", "/books/" + id, null);
        assertEquals(204, deleted.statusCode());

        HttpResponse<String> fetched = send("GET", "/books/" + id, null);
        assertEquals(404, fetched.statusCode());

        HttpResponse<String> deletedAgain = send("DELETE", "/books/" + id, null);
        assertEquals(404, deletedAgain.statusCode());
    }

    @Test
    void getMissingBookReturns404() throws Exception {
        HttpResponse<String> res = send("GET", "/books/424242", null);
        assertEquals(404, res.statusCode());
        assertTrue(GSON.fromJson(res.body(), JsonObject.class).has("error"));
    }

    private static HttpResponse<String> send(String method, String path, String jsonBody) throws Exception {
        HttpRequest.Builder builder = HttpRequest.newBuilder().uri(URI.create(base + path));
        if (jsonBody != null) {
            builder.header("Content-Type", "application/json");
            builder.method(method, HttpRequest.BodyPublishers.ofString(jsonBody));
        } else {
            builder.method(method, HttpRequest.BodyPublishers.noBody());
        }
        return client.send(builder.build(), HttpResponse.BodyHandlers.ofString());
    }
}
