package com.example.bookstore;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;

import java.io.IOException;
import java.io.OutputStream;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class BookStoreHandler implements HttpHandler {

    private static final Pattern ID_ROUTE = Pattern.compile("^/books/([0-9]+)/?$");
    private static final Pattern COLLECTION_ROUTE = Pattern.compile("^/books/?$");
    private static final Pattern HEALTH_ROUTE = Pattern.compile("^/health/?$");

    private final BookDao dao;

    public BookStoreHandler(BookDao dao) {
        this.dao = dao;
    }

    @Override
    public void handle(HttpExchange exchange) throws IOException {
        try {
            RouteResult result = route(exchange);
            byte[] body = result.body() == null ? new byte[0] : result.body().getBytes(StandardCharsets.UTF_8);
            writeResponse(exchange, result.status(), body);
        } catch (Exception e) {
            String payload = "{\"errors\":[\"internal server error: " + escape(e.getMessage()) + "\"]}";
            writeResponse(exchange, 500, payload.getBytes(StandardCharsets.UTF_8));
        } finally {
            exchange.close();
        }
    }

    private RouteResult route(HttpExchange exchange) throws Exception {
        String method = exchange.getRequestMethod();
        URI uri = exchange.getRequestURI();
        String path = uri.getPath();
        String rawBody = readBody(exchange);
        Map<String, String> query = parseQuery(uri.getQuery());

        Matcher health = HEALTH_ROUTE.matcher(path);
        if (health.matches()) {
            if (!"GET".equalsIgnoreCase(method)) return new RouteResult(405, "{\"errors\":[\"method not allowed\"]}");
            return new RouteResult(200, "{\"status\":\"up\"}");
        }

        Matcher collection = COLLECTION_ROUTE.matcher(path);
        if (collection.matches()) {
            if ("GET".equalsIgnoreCase(method)) {
                String author = query.get("author");
                List<Book> books = dao.list(author);
                return new RouteResult(200, Json.toJson(books));
            }
            if ("POST".equalsIgnoreCase(method)) {
                if (rawBody.isBlank()) return new RouteResult(400, "{\"errors\":[\"body is required\"]}");
                Book book;
                try {
                    book = Json.fromJson(rawBody, Book.class);
                } catch (Exception ex) {
                    return new RouteResult(400, "{\"errors\":[\"malformed JSON: " + escape(ex.getMessage()) + "\"]}");
                }
                List<String> errors = Validator.validate(book);
                if (!errors.isEmpty()) {
                    return new RouteResult(400, Json.toJson(Map.of("errors", errors)));
                }
                Book saved = dao.create(book);
                return new RouteResult(201, Json.toJson(saved));
            }
            return new RouteResult(405, "{\"errors\":[\"method not allowed\"]}");
        }

        Matcher idRoute = ID_ROUTE.matcher(path);
        if (idRoute.matches()) {
            long id = Long.parseLong(idRoute.group(1));
            if ("GET".equalsIgnoreCase(method)) {
                Optional<Book> book = dao.get(id);
                if (book.isEmpty()) return new RouteResult(404, "{\"errors\":[\"book not found\"]}");
                return new RouteResult(200, Json.toJson(book.get()));
            }
            if ("PUT".equalsIgnoreCase(method)) {
                if (rawBody.isBlank()) return new RouteResult(400, "{\"errors\":[\"body is required\"]}");
                Book book;
                try {
                    book = Json.fromJson(rawBody, Book.class);
                } catch (Exception ex) {
                    return new RouteResult(400, "{\"errors\":[\"malformed JSON: " + escape(ex.getMessage()) + "\"]}");
                }
                List<String> errors = Validator.validate(book);
                if (!errors.isEmpty()) {
                    return new RouteResult(400, Json.toJson(Map.of("errors", errors)));
                }
                if (!dao.update(id, book)) {
                    return new RouteResult(404, "{\"errors\":[\"book not found\"]}");
                }
                book.setId(id);
                return new RouteResult(200, Json.toJson(book));
            }
            if ("DELETE".equalsIgnoreCase(method)) {
                if (!dao.delete(id)) return new RouteResult(404, "{\"errors\":[\"book not found\"]}");
                return new RouteResult(204, null);
            }
            return new RouteResult(405, "{\"errors\":[\"method not allowed\"]}");
        }

        return new RouteResult(404, "{\"errors\":[\"not found\"]}");
    }

    private void writeResponse(HttpExchange exchange, int status, byte[] body) throws IOException {
        if (body == null) body = new byte[0];
        exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        exchange.sendResponseHeaders(status, body.length == 0 ? -1 : body.length);
        try (OutputStream os = exchange.getResponseBody()) {
            os.write(body);
        }
    }

    private String readBody(HttpExchange exchange) throws IOException {
        byte[] bytes = exchange.getRequestBody().readAllBytes();
        return new String(bytes, StandardCharsets.UTF_8);
    }

    private Map<String, String> parseQuery(String query) {
        Map<String, String> map = new HashMap<>();
        if (query == null || query.isEmpty()) return map;
        for (String pair : query.split("&")) {
            int idx = pair.indexOf('=');
            String key;
            String value;
            if (idx < 0) {
                key = pair;
                value = "";
            } else {
                key = pair.substring(0, idx);
                value = pair.substring(idx + 1);
            }
            map.put(key, java.net.URLDecoder.decode(value, StandardCharsets.UTF_8));
        }
        return map;
    }

    private static String escape(String s) {
        if (s == null) return "";
        return s.replace("\\", "\\\\").replace("\"", "\\\"");
    }

    private record RouteResult(int status, String body) {}
}
