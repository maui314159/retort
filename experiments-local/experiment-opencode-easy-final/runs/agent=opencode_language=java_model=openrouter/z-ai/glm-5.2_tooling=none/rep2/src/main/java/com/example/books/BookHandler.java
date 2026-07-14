package com.example.books;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;

import java.io.IOException;
import java.util.List;
import java.util.Map;

public class BookHandler implements HttpHandler {

    private final BookRepository repository;

    public BookHandler(BookRepository repository) {
        this.repository = repository;
    }

    @Override
    public void handle(HttpExchange exchange) throws IOException {
        try {
            String method = exchange.getRequestMethod();
            String path = exchange.getRequestURI().getPath();
            String[] segments = path.split("/");
            // path = "/books" or "/books/{id}"
            String idSegment = segments.length >= 3 ? segments[2] : null;
            Long id = parseId(idSegment);

            switch (method) {
                case "POST" -> handleCreate(exchange);
                case "GET" -> {
                    if (id == null) handleList(exchange);
                    else handleGetOne(exchange, id);
                }
                case "PUT" -> {
                    if (id == null) HttpUtil.sendError(exchange, 400, "Missing book id in path");
                    else handleUpdate(exchange, id);
                }
                case "DELETE" -> {
                    if (id == null) HttpUtil.sendError(exchange, 400, "Missing book id in path");
                    else handleDelete(exchange, id);
                }
                default -> HttpUtil.sendError(exchange, 405, "Method not allowed: " + method);
            }
        } catch (ValidationException ve) {
            HttpUtil.sendError(exchange, 400, ve.getMessage());
        } catch (Exception e) {
            HttpUtil.sendError(exchange, 500, "Internal server error: " + e.getMessage());
        } finally {
            exchange.close();
        }
    }

    private Long parseId(String segment) {
        if (segment == null || segment.isBlank()) return null;
        try {
            return Long.parseLong(segment);
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private void handleCreate(HttpExchange exchange) throws IOException, ValidationException, java.sql.SQLException {
        Book input = JsonUtil.fromJson(exchange.getRequestBody(), Book.class);
        validate(input);
        Book saved = repository.create(input);
        HttpUtil.sendJson(exchange, 201, saved);
    }

    private void handleList(HttpExchange exchange) throws IOException, java.sql.SQLException {
        Map<String, String> q = HttpUtil.parseQuery(exchange.getRequestURI().getRawQuery());
        String author = q.get("author");
        List<Book> books = repository.findAll(author);
        HttpUtil.sendJson(exchange, 200, books);
    }

    private void handleGetOne(HttpExchange exchange, Long id) throws IOException, java.sql.SQLException {
        Book book = repository.findById(id);
        if (book == null) HttpUtil.sendError(exchange, 404, "Book not found: " + id);
        else HttpUtil.sendJson(exchange, 200, book);
    }

    private void handleUpdate(HttpExchange exchange, Long id) throws IOException, ValidationException, java.sql.SQLException {
        Book input = JsonUtil.fromJson(exchange.getRequestBody(), Book.class);
        validate(input);
        boolean updated = repository.update(id, input);
        if (!updated) {
            HttpUtil.sendError(exchange, 404, "Book not found: " + id);
            return;
        }
        Book refreshed = repository.findById(id);
        HttpUtil.sendJson(exchange, 200, refreshed);
    }

    private void handleDelete(HttpExchange exchange, Long id) throws IOException, java.sql.SQLException {
        boolean deleted = repository.delete(id);
        if (!deleted) HttpUtil.sendError(exchange, 404, "Book not found: " + id);
        else HttpUtil.sendNoContent(exchange, 204);
    }

    private void validate(Book book) throws ValidationException {
        if (book == null) throw new ValidationException("Request body is required");
        if (book.getTitle() == null || book.getTitle().isBlank())
            throw new ValidationException("title is required");
        if (book.getAuthor() == null || book.getAuthor().isBlank())
            throw new ValidationException("author is required");
    }
}
