package com.example.books;

import com.fasterxml.jackson.databind.JsonNode;
import com.sun.net.httpserver.Headers;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;

import java.io.IOException;
import java.io.OutputStream;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

public class BookHandler implements HttpHandler {

    private final BookRepository repository;

    public BookHandler(BookRepository repository) {
        this.repository = repository;
    }

    @Override
    public void handle(HttpExchange exchange) throws IOException {
        String path = exchange.getRequestURI().getPath();
        String method = exchange.getRequestMethod();
        try {
            // Normalize trailing slash
            if (path.endsWith("/") && path.length() > 1) {
                path = path.replaceAll("/+$", "");
            }

            if (!path.startsWith("/books")) {
                writeJson(exchange, 404, JsonUtil.errorJson("Not found"));
                return;
            }

            String sub = path.substring("/books".length());
            if (sub.isEmpty() || sub.equals("/")) {
                if ("GET".equals(method)) {
                    handleList(exchange);
                } else if ("POST".equals(method)) {
                    handleCreate(exchange);
                } else {
                    writeJson(exchange, 405, JsonUtil.errorJson("Method not allowed"));
                }
                return;
            }

            if (!sub.startsWith("/")) {
                writeJson(exchange, 404, JsonUtil.errorJson("Not found"));
                return;
            }
            String idPart = sub.substring(1);
            long id;
            try {
                id = Long.parseLong(idPart);
            } catch (NumberFormatException e) {
                writeJson(exchange, 404, JsonUtil.errorJson("Not found"));
                return;
            }

            switch (method) {
                case "GET":
                    handleGet(exchange, id);
                    break;
                case "PUT":
                    handleUpdate(exchange, id);
                    break;
                case "DELETE":
                    handleDelete(exchange, id);
                    break;
                default:
                    writeJson(exchange, 405, JsonUtil.errorJson("Method not allowed"));
            }
        } catch (Exception e) {
            writeJson(exchange, 500, JsonUtil.errorJson("Internal server error: " + e.getMessage()));
        } finally {
            exchange.close();
        }
    }

    private void handleList(HttpExchange exchange) throws IOException {
        Map<String, String> query = parseQuery(exchange.getRequestURI().getRawQuery());
        String author = query.get("author");
        String body = JsonUtil.toJson(repository.findAll(author));
        writeJson(exchange, 200, body);
    }

    private void handleCreate(HttpExchange exchange) throws IOException {
        JsonNode root = JsonUtil.parse(readBody(exchange));
        ValidationResult vr = validate(root, true);
        if (vr.invalid) {
            writeJson(exchange, 400, JsonUtil.errorJson(vr.message));
            return;
        }
        Book book = toBook(root);
        Book created = repository.create(book);
        writeJson(exchange, 201, JsonUtil.toJson(created));
    }

    private void handleGet(HttpExchange exchange, long id) throws IOException {
        Book book = repository.findById(id).orElse(null);
        if (book == null) {
            writeJson(exchange, 404, JsonUtil.errorJson("Book not found"));
        } else {
            writeJson(exchange, 200, JsonUtil.toJson(book));
        }
    }

    private void handleUpdate(HttpExchange exchange, long id) throws IOException {
        JsonNode root = JsonUtil.parse(readBody(exchange));
        ValidationResult vr = validate(root, true);
        if (vr.invalid) {
            writeJson(exchange, 400, JsonUtil.errorJson(vr.message));
            return;
        }
        Book book = toBook(root);
        if (!repository.update(id, book)) {
            writeJson(exchange, 404, JsonUtil.errorJson("Book not found"));
            return;
        }
        writeJson(exchange, 200, JsonUtil.toJson(book));
    }

    private void handleDelete(HttpExchange exchange, long id) throws IOException {
        if (!repository.delete(id)) {
            writeJson(exchange, 404, JsonUtil.errorJson("Book not found"));
            return;
        }
        writeJson(exchange, 204, "");
    }

    private Book toBook(JsonNode root) {
        Book book = new Book();
        book.setTitle(textOrNull(root, "title"));
        book.setAuthor(textOrNull(root, "author"));
        if (root.has("year") && !root.get("year").isNull()) {
            book.setYear(root.get("year").asInt());
        }
        if (root.has("isbn") && !root.get("isbn").isNull()) {
            book.setIsbn(root.get("isbn").asText());
        }
        return book;
    }

    private String textOrNull(JsonNode root, String field) {
        if (root.has(field) && !root.get(field).isNull()) {
            return root.get(field).asText();
        }
        return null;
    }

    private ValidationResult validate(JsonNode root, boolean requireCore) {
        if (requireCore) {
            if (!root.has("title") || root.get("title").isNull()
                    || root.get("title").asText().isBlank()) {
                return new ValidationResult(true, "title is required");
            }
            if (!root.has("author") || root.get("author").isNull()
                    || root.get("author").asText().isBlank()) {
                return new ValidationResult(true, "author is required");
            }
        }
        if (root.has("year") && !root.get("year").isNull()) {
            JsonNode y = root.get("year");
            if (!y.isNumber() || !y.canConvertToInt()) {
                return new ValidationResult(true, "year must be an integer");
            }
        }
        return new ValidationResult(false, null);
    }

    private String readBody(HttpExchange exchange) throws IOException {
        byte[] bytes = exchange.getRequestBody().readAllBytes();
        return new String(bytes, StandardCharsets.UTF_8);
    }

    private Map<String, String> parseQuery(String rawQuery) {
        Map<String, String> map = new HashMap<>();
        if (rawQuery == null || rawQuery.isEmpty()) {
            return map;
        }
        for (String pair : rawQuery.split("&")) {
            int idx = pair.indexOf('=');
            String key;
            String value = "";
            if (idx >= 0) {
                key = URLDecoder.decode(pair.substring(0, idx), StandardCharsets.UTF_8);
                value = URLDecoder.decode(pair.substring(idx + 1), StandardCharsets.UTF_8);
            } else {
                key = URLDecoder.decode(pair, StandardCharsets.UTF_8);
            }
            map.put(key, value);
        }
        return map;
    }

    private void writeJson(HttpExchange exchange, int status, String body) throws IOException {
        Headers headers = exchange.getResponseHeaders();
        if (status != 204) {
            headers.set("Content-Type", "application/json; charset=utf-8");
        }
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        exchange.sendResponseHeaders(status, bytes.length == 0 ? -1 : bytes.length);
        try (OutputStream os = exchange.getResponseBody()) {
            if (bytes.length > 0) {
                os.write(bytes);
            }
        }
    }

    private static class ValidationResult {
        final boolean invalid;
        final String message;

        ValidationResult(boolean invalid, String message) {
            this.invalid = invalid;
            this.message = message;
        }
    }
}
