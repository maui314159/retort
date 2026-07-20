package com.example.books;

import com.google.gson.Gson;
import com.google.gson.JsonSyntaxException;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;

import java.io.IOException;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.sql.SQLException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Routes requests under {@code /books} to the CRUD operations:
 * <ul>
 *   <li>POST   /books       — create a book (201; 400 on validation failure)</li>
 *   <li>GET    /books       — list books, optional {@code ?author=} filter (200)</li>
 *   <li>GET    /books/{id}  — fetch one book (200, 404)</li>
 *   <li>PUT    /books/{id}  — replace a book (200; 400 on validation failure, 404)</li>
 *   <li>DELETE /books/{id}  — delete a book (204, 404)</li>
 * </ul>
 */
public class BookHandler implements HttpHandler {

    private static final Gson GSON = new Gson();

    private final BookRepository repo;

    public BookHandler(BookRepository repo) {
        this.repo = repo;
    }

    @Override
    public void handle(HttpExchange exchange) throws IOException {
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
        String method = exchange.getRequestMethod();

        if (path.equals("/books") || path.equals("/books/")) {
            switch (method) {
                case "GET" -> listBooks(exchange);
                case "POST" -> createBook(exchange);
                default -> sendError(exchange, 405, "Method not allowed");
            }
            return;
        }

        if (path.startsWith("/books/")) {
            String idPart = path.substring("/books/".length());
            long id;
            try {
                id = Long.parseLong(idPart);
            } catch (NumberFormatException e) {
                sendError(exchange, 404, "Book not found");
                return;
            }
            switch (method) {
                case "GET" -> getBook(exchange, id);
                case "PUT" -> updateBook(exchange, id);
                case "DELETE" -> deleteBook(exchange, id);
                default -> sendError(exchange, 405, "Method not allowed");
            }
            return;
        }

        sendError(exchange, 404, "Not found");
    }

    private void listBooks(HttpExchange exchange) throws IOException, SQLException {
        String author = queryParams(exchange.getRequestURI().getRawQuery()).get("author");
        List<Book> books = repo.findAll(author);
        sendJson(exchange, 200, books);
    }

    private void createBook(HttpExchange exchange) throws IOException, SQLException {
        Book input = parseBody(exchange);
        if (input == null) {
            sendError(exchange, 400, "Request body must be valid JSON");
            return;
        }
        if (isBlank(input.getTitle()) || isBlank(input.getAuthor())) {
            sendError(exchange, 400, "title and author are required");
            return;
        }
        Book created = repo.create(input);
        sendJson(exchange, 201, created);
    }

    private void getBook(HttpExchange exchange, long id) throws IOException, SQLException {
        Optional<Book> book = repo.findById(id);
        if (book.isPresent()) {
            sendJson(exchange, 200, book.get());
        } else {
            sendError(exchange, 404, "Book not found");
        }
    }

    private void updateBook(HttpExchange exchange, long id) throws IOException, SQLException {
        Book input = parseBody(exchange);
        if (input == null) {
            sendError(exchange, 400, "Request body must be valid JSON");
            return;
        }
        if (isBlank(input.getTitle()) || isBlank(input.getAuthor())) {
            sendError(exchange, 400, "title and author are required");
            return;
        }
        if (repo.update(id, input)) {
            input.setId(id);
            sendJson(exchange, 200, input);
        } else {
            sendError(exchange, 404, "Book not found");
        }
    }

    private void deleteBook(HttpExchange exchange, long id) throws IOException, SQLException {
        if (repo.delete(id)) {
            exchange.sendResponseHeaders(204, -1);
        } else {
            sendError(exchange, 404, "Book not found");
        }
    }

    private static Book parseBody(HttpExchange exchange) throws IOException {
        String body = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
        try {
            return GSON.fromJson(body, Book.class);
        } catch (JsonSyntaxException e) {
            return null;
        }
    }

    private static Map<String, String> queryParams(String rawQuery) {
        Map<String, String> params = new HashMap<>();
        if (rawQuery == null || rawQuery.isEmpty()) {
            return params;
        }
        for (String pair : rawQuery.split("&")) {
            int eq = pair.indexOf('=');
            if (eq > 0) {
                String key = URLDecoder.decode(pair.substring(0, eq), StandardCharsets.UTF_8);
                String value = URLDecoder.decode(pair.substring(eq + 1), StandardCharsets.UTF_8);
                params.put(key, value);
            }
        }
        return params;
    }

    private static boolean isBlank(String s) {
        return s == null || s.isBlank();
    }

    static void sendJson(HttpExchange exchange, int status, Object payload) throws IOException {
        byte[] bytes = GSON.toJson(payload).getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "application/json");
        exchange.sendResponseHeaders(status, bytes.length);
        exchange.getResponseBody().write(bytes);
    }

    static void sendError(HttpExchange exchange, int status, String message) throws IOException {
        sendJson(exchange, status, Map.of("error", message));
    }
}
