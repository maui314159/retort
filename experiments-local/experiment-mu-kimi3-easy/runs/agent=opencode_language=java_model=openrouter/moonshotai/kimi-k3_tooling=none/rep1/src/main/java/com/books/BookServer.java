package com.books;

import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.Executors;

/**
 * HTTP layer for the book service, built on the JDK's embedded
 * {@link HttpServer}. Routes:
 *
 * <pre>
 *   GET    /health
 *   POST   /books
 *   GET    /books[?author=...]
 *   GET    /books/{id}
 *   PUT    /books/{id}
 *   DELETE /books/{id}
 * </pre>
 */
public class BookServer {

    private final HttpServer server;
    private final BookRepository repository;

    public BookServer(int port, String dbPath) throws IOException {
        this.repository = new BookRepository(dbPath);
        this.server = HttpServer.create(new InetSocketAddress(port), 0);
        this.server.createContext("/", new Router(repository));
        this.server.setExecutor(Executors.newVirtualThreadPerTaskExecutor());
    }

    public void start() {
        server.start();
    }

    public void stop() {
        server.stop(0);
    }

    /** Actual bound port (useful when constructed with port 0). */
    public int getPort() {
        return server.getAddress().getPort();
    }

    static class Router implements HttpHandler {

        private static final ObjectMapper MAPPER = new ObjectMapper()
                .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);

        private final BookRepository repository;

        Router(BookRepository repository) {
            this.repository = repository;
        }

        @Override
        public void handle(HttpExchange exchange) throws IOException {
            try {
                route(exchange);
            } catch (Exception e) {
                sendJson(exchange, 500, error("internal server error"));
            } finally {
                exchange.close();
            }
        }

        private void route(HttpExchange exchange) throws IOException {
            String method = exchange.getRequestMethod();
            String path = exchange.getRequestURI().getPath();

            if (path.equals("/health")) {
                if (method.equals("GET")) {
                    sendJson(exchange, 200, Map.of("status", "ok"));
                } else {
                    methodNotAllowed(exchange);
                }
                return;
            }

            if (path.equals("/books")) {
                switch (method) {
                    case "GET" -> listBooks(exchange);
                    case "POST" -> createBook(exchange);
                    default -> methodNotAllowed(exchange);
                }
                return;
            }

            if (path.startsWith("/books/")) {
                Long id = parseId(path.substring("/books/".length()));
                if (id == null) {
                    sendJson(exchange, 404, error("book not found"));
                    return;
                }
                switch (method) {
                    case "GET" -> getBook(exchange, id);
                    case "PUT" -> updateBook(exchange, id);
                    case "DELETE" -> deleteBook(exchange, id);
                    default -> methodNotAllowed(exchange);
                }
                return;
            }

            sendJson(exchange, 404, error("not found"));
        }

        private void listBooks(HttpExchange exchange) throws IOException {
            String author = parseQuery(exchange.getRequestURI().getRawQuery()).get("author");
            List<Book> books = repository.findAll(author);
            sendJson(exchange, 200, books);
        }

        private void createBook(HttpExchange exchange) throws IOException {
            Book book = readBody(exchange);
            if (book == null) return; // 400 already sent
            if (!isValid(book)) {
                sendJson(exchange, 400, error("title and author are required"));
                return;
            }
            book.setId(null); // ignore any client-supplied id
            sendJson(exchange, 201, repository.create(book));
        }

        private void getBook(HttpExchange exchange, long id) throws IOException {
            Optional<Book> book = repository.findById(id);
            if (book.isPresent()) {
                sendJson(exchange, 200, book.get());
            } else {
                sendJson(exchange, 404, error("book not found"));
            }
        }

        private void updateBook(HttpExchange exchange, long id) throws IOException {
            Book book = readBody(exchange);
            if (book == null) return; // 400 already sent
            if (!isValid(book)) {
                sendJson(exchange, 400, error("title and author are required"));
                return;
            }
            book.setId(id);
            if (repository.update(book)) {
                sendJson(exchange, 200, book);
            } else {
                sendJson(exchange, 404, error("book not found"));
            }
        }

        private void deleteBook(HttpExchange exchange, long id) throws IOException {
            if (repository.delete(id)) {
                exchange.sendResponseHeaders(204, -1);
            } else {
                sendJson(exchange, 404, error("book not found"));
            }
        }

        /** Parses the JSON request body, or sends a 400 and returns null. */
        private Book readBody(HttpExchange exchange) throws IOException {
            try {
                return MAPPER.readValue(exchange.getRequestBody(), Book.class);
            } catch (Exception e) {
                sendJson(exchange, 400, error("invalid JSON body"));
                return null;
            }
        }

        private static boolean isValid(Book book) {
            return book.getTitle() != null && !book.getTitle().isBlank()
                    && book.getAuthor() != null && !book.getAuthor().isBlank();
        }

        private void methodNotAllowed(HttpExchange exchange) throws IOException {
            sendJson(exchange, 405, error("method not allowed"));
        }

        private static Long parseId(String segment) {
            if (segment.isEmpty() || !segment.chars().allMatch(Character::isDigit)) {
                return null;
            }
            try {
                return Long.parseLong(segment);
            } catch (NumberFormatException e) {
                return null;
            }
        }

        private static Map<String, String> parseQuery(String rawQuery) {
            Map<String, String> params = new LinkedHashMap<>();
            if (rawQuery == null || rawQuery.isEmpty()) {
                return params;
            }
            for (String pair : rawQuery.split("&")) {
                int idx = pair.indexOf('=');
                if (idx < 0) {
                    params.put(urlDecode(pair), "");
                } else {
                    params.put(urlDecode(pair.substring(0, idx)), urlDecode(pair.substring(idx + 1)));
                }
            }
            return params;
        }

        private static String urlDecode(String value) {
            return URLDecoder.decode(value, StandardCharsets.UTF_8);
        }

        private static Map<String, String> error(String message) {
            return Map.of("error", message);
        }

        private static void sendJson(HttpExchange exchange, int status, Object body) throws IOException {
            byte[] bytes = MAPPER.writeValueAsBytes(body);
            exchange.getResponseHeaders().set("Content-Type", "application/json");
            exchange.sendResponseHeaders(status, bytes.length);
            try (OutputStream os = exchange.getResponseBody()) {
                os.write(bytes);
            }
        }
    }
}
