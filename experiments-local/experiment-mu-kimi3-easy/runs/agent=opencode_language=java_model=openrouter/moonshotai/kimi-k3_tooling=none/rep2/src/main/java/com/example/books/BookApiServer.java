package com.example.books;

import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.sql.SQLException;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.Executors;

/**
 * Why: TASK.md requires a JSON REST API: CRUD on /books plus GET /health.
 * What: routes /books and /books/{id} to the repository and maps outcomes to HTTP
 * status codes — 201 create, 200 read/update, 204 delete, 400 invalid input,
 * 404 unknown book, 405 wrong method, 500 storage failure. All responses are JSON.
 */
public class BookApiServer {

    private final HttpServer server;
    private final BookRepository repository;
    private final ObjectMapper mapper;

    public BookApiServer(int port, BookRepository repository) throws IOException {
        this.repository = repository;
        this.mapper = new ObjectMapper()
                .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);
        this.server = HttpServer.create(new InetSocketAddress(port), 0);
        server.createContext("/health", this::handleHealth);
        server.createContext("/books", this::handleBooks);
        server.setExecutor(Executors.newFixedThreadPool(8));
    }

    public void start() {
        server.start();
    }

    public void stop() {
        server.stop(0);
    }

    public int getPort() {
        return server.getAddress().getPort();
    }

    private void handleHealth(HttpExchange exchange) throws IOException {
        try {
            if (!"GET".equals(exchange.getRequestMethod())) {
                sendError(exchange, 405, "Method not allowed");
                return;
            }
            sendJson(exchange, 200, Map.of("status", "ok"));
        } finally {
            exchange.close();
        }
    }

    private void handleBooks(HttpExchange exchange) throws IOException {
        try {
            route(exchange);
        } catch (SQLException e) {
            sendError(exchange, 500, "Internal server error");
        } finally {
            exchange.close();
        }
    }

    private void route(HttpExchange exchange) throws IOException, SQLException {
        String path = exchange.getRequestURI().getPath();
        String rest = path.substring("/books".length());
        String method = exchange.getRequestMethod();

        if (rest.isEmpty() || rest.equals("/")) {
            switch (method) {
                case "GET" -> listBooks(exchange);
                case "POST" -> createBook(exchange);
                default -> sendError(exchange, 405, "Method not allowed");
            }
        } else if (rest.matches("/\\d+")) {
            int id = Integer.parseInt(rest.substring(1));
            switch (method) {
                case "GET" -> getBook(exchange, id);
                case "PUT" -> updateBook(exchange, id);
                case "DELETE" -> deleteBook(exchange, id);
                default -> sendError(exchange, 405, "Method not allowed");
            }
        } else if (rest.matches("/[^/]+")) {
            sendError(exchange, 400, "Invalid book id");
        } else {
            sendError(exchange, 404, "Not found");
        }
    }

    private void listBooks(HttpExchange exchange) throws IOException, SQLException {
        String author = queryParam(exchange.getRequestURI().getRawQuery(), "author");
        List<Book> books = repository.findAll(author);
        sendJson(exchange, 200, books);
    }

    private void createBook(HttpExchange exchange) throws IOException, SQLException {
        Book book = readBody(exchange);
        if (book == null) {
            return;
        }
        String error = validate(book);
        if (error != null) {
            sendError(exchange, 400, error);
            return;
        }
        sendJson(exchange, 201, repository.create(book));
    }

    private void getBook(HttpExchange exchange, int id) throws IOException, SQLException {
        Optional<Book> book = repository.findById(id);
        if (book.isPresent()) {
            sendJson(exchange, 200, book.get());
        } else {
            sendError(exchange, 404, "Book not found");
        }
    }

    private void updateBook(HttpExchange exchange, int id) throws IOException, SQLException {
        Book book = readBody(exchange);
        if (book == null) {
            return;
        }
        String error = validate(book);
        if (error != null) {
            sendError(exchange, 400, error);
            return;
        }
        book.setId(id);
        if (repository.update(book)) {
            sendJson(exchange, 200, book);
        } else {
            sendError(exchange, 404, "Book not found");
        }
    }

    private void deleteBook(HttpExchange exchange, int id) throws IOException, SQLException {
        if (repository.delete(id)) {
            exchange.sendResponseHeaders(204, -1);
        } else {
            sendError(exchange, 404, "Book not found");
        }
    }

    /** Returns null (after sending a 400) when the body is not valid JSON. */
    private Book readBody(HttpExchange exchange) throws IOException {
        try {
            return mapper.readValue(exchange.getRequestBody(), Book.class);
        } catch (Exception e) {
            sendError(exchange, 400, "Invalid JSON body");
            return null;
        }
    }

    private static String validate(Book book) {
        if (book.getTitle() == null || book.getTitle().isBlank()) {
            return "title is required";
        }
        if (book.getAuthor() == null || book.getAuthor().isBlank()) {
            return "author is required";
        }
        return null;
    }

    private static String queryParam(String rawQuery, String name) {
        if (rawQuery == null) {
            return null;
        }
        for (String pair : rawQuery.split("&")) {
            int eq = pair.indexOf('=');
            if (eq > 0 && URLDecoder.decode(pair.substring(0, eq), StandardCharsets.UTF_8).equals(name)) {
                return URLDecoder.decode(pair.substring(eq + 1), StandardCharsets.UTF_8);
            }
        }
        return null;
    }

    private void sendJson(HttpExchange exchange, int status, Object body) throws IOException {
        byte[] bytes = mapper.writeValueAsBytes(body);
        exchange.getResponseHeaders().set("Content-Type", "application/json");
        exchange.sendResponseHeaders(status, bytes.length);
        try (OutputStream os = exchange.getResponseBody()) {
            os.write(bytes);
        }
    }

    private void sendError(HttpExchange exchange, int status, String message) throws IOException {
        sendJson(exchange, status, Map.of("error", message));
    }
}
