package com.example;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.exc.MismatchedInputException;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.sql.SQLException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Executors;

public class Router implements AutoCloseable {

    private final HttpServer server;
    private final ObjectMapper mapper = new ObjectMapper();

    public Router(BookService service, int port) throws IOException {
        this.server = HttpServer.create(new InetSocketAddress(port), 0);
        server.setExecutor(Executors.newFixedThreadPool(8));
        server.createContext("/", new RootHandler(service));
    }

    public int port() {
        InetSocketAddress addr = server.getAddress();
        return addr == null ? -1 : addr.getPort();
    }

    public void start() { server.start(); }

    @Override
    public void close() {
        server.stop(0);
    }

    private class RootHandler implements HttpHandler {
        private final BookService service;

        RootHandler(BookService service) { this.service = service; }

        @Override
        public void handle(HttpExchange exchange) throws IOException {
            try {
                String method = exchange.getRequestMethod();
                String path = exchange.getRequestURI().getPath();
                dispatch(exchange, method, path);
            } catch (Exception e) {
                sendError(exchange, 500, "internal server error: " + e.getMessage());
            } finally {
                exchange.close();
            }
        }

        private void dispatch(HttpExchange exchange, String method, String path) throws IOException {
            if ("/health".equals(path)) {
                if ("GET".equals(method)) {
                    sendJson(exchange, 200, Map.of("status", "up"));
                } else {
                    sendError(exchange, 405, "method not allowed");
                }
                return;
            }

            if ("/books".equals(path)) {
                switch (method) {
                    case "POST" -> handleCreate(exchange);
                    case "GET" -> handleList(exchange);
                    default -> sendError(exchange, 405, "method not allowed");
                }
                return;
            }

            if (path.startsWith("/books/")) {
                String tail = path.substring("/books/".length());
                Long id;
                try {
                    id = Long.parseLong(tail);
                } catch (NumberFormatException e) {
                    sendError(exchange, 404, "not found");
                    return;
                }
                switch (method) {
                    case "GET" -> handleGet(exchange, id);
                    case "PUT" -> handleUpdate(exchange, id);
                    case "DELETE" -> handleDelete(exchange, id);
                    default -> sendError(exchange, 405, "method not allowed");
                }
                return;
            }

            sendError(exchange, 404, "not found");
        }

        private void handleCreate(HttpExchange exchange) throws IOException {
            Book input = readBody(exchange);
            if (input == null) {
                sendError(exchange, 400, "request body is required");
                return;
            }
            try {
                Book created = service.create(input);
                sendJson(exchange, 201, created);
            } catch (ValidationException e) {
                sendError(exchange, 400, Map.of("error", "validation failed", "field", e.getField(), "message", e.getMessage()));
            } catch (SQLException e) {
                sendError(exchange, 500, "database error: " + e.getMessage());
            }
        }

        private void handleList(HttpExchange exchange) throws IOException {
            Map<String, String> params = queryParams(exchange.getRequestURI());
            String author = params.get("author");
            try {
                List<Book> books = service.list(author);
                sendJson(exchange, 200, books);
            } catch (SQLException e) {
                sendError(exchange, 500, "database error: " + e.getMessage());
            }
        }

        private void handleGet(HttpExchange exchange, Long id) throws IOException {
            try {
                Book b = service.get(id);
                if (b == null) {
                    sendError(exchange, 404, "book not found");
                } else {
                    sendJson(exchange, 200, b);
                }
            } catch (SQLException e) {
                sendError(exchange, 500, "database error: " + e.getMessage());
            }
        }

        private void handleUpdate(HttpExchange exchange, Long id) throws IOException {
            Book input = readBody(exchange);
            if (input == null) {
                sendError(exchange, 400, "request body is required");
                return;
            }
            try {
                Book updated = service.update(id, input);
                sendJson(exchange, 200, updated);
            } catch (ValidationException e) {
                sendError(exchange, 400, Map.of("error", "validation failed", "field", e.getField(), "message", e.getMessage()));
            } catch (NotFoundException e) {
                sendError(exchange, 404, "book not found");
            } catch (SQLException e) {
                sendError(exchange, 500, "database error: " + e.getMessage());
            }
        }

        private void handleDelete(HttpExchange exchange, Long id) throws IOException {
            try {
                service.delete(id);
                sendJson(exchange, 204, null);
            } catch (NotFoundException e) {
                sendError(exchange, 404, "book not found");
            } catch (SQLException e) {
                sendError(exchange, 500, "database error: " + e.getMessage());
            }
        }

        private Book readBody(HttpExchange exchange) throws IOException {
            try (InputStream is = exchange.getRequestBody()) {
                byte[] bytes = is.readAllBytes();
                if (bytes.length == 0) return null;
                return mapper.readValue(bytes, Book.class);
            } catch (MismatchedInputException e) {
                return null;
            }
        }

        private void sendJson(HttpExchange exchange, int status, Object body) throws IOException {
            byte[] payload = body == null ? new byte[0] : mapper.writeValueAsBytes(body);
            if (payload.length == 0) {
                exchange.getResponseHeaders().set("Content-Type", "application/json");
                exchange.sendResponseHeaders(status, -1);
                return;
            }
            exchange.getResponseHeaders().set("Content-Type", "application/json");
            exchange.sendResponseHeaders(status, payload.length);
            try (OutputStream os = exchange.getResponseBody()) {
                os.write(payload);
            }
        }

        private void sendError(HttpExchange exchange, int status, String message) throws IOException {
            sendJson(exchange, status, Map.of("error", message));
        }

        private void sendError(HttpExchange exchange, int status, Map<String, Object> body) throws IOException {
            sendJson(exchange, status, body);
        }

        private Map<String, String> queryParams(URI uri) {
            Map<String, String> params = new HashMap<>();
            String query = uri.getQuery();
            if (query == null || query.isEmpty()) return params;
            for (String pair : query.split("&")) {
                String[] kv = pair.split("=", 2);
                String key = java.net.URLDecoder.decode(kv[0], StandardCharsets.UTF_8);
                String value = kv.length > 1 ? java.net.URLDecoder.decode(kv[1], StandardCharsets.UTF_8) : "";
                params.put(key, value);
            }
            return params;
        }
    }
}
