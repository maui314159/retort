package com.example.books;

import java.sql.SQLException;
import java.util.Map;
import java.util.Objects;

import io.javalin.http.Context;
import io.javalin.http.HttpStatus;

/**
 * HTTP routing for the {@code /books} resource plus the {@code /health}
 * probe. The controller is intentionally thin: parse, validate, delegate
 * to the repository, render the response.
 */
public final class BookController {

    private final BookRepository repository;

    public BookController(BookRepository repository) {
        this.repository = Objects.requireNonNull(repository, "repository");
    }

    public void register(io.javalin.Javalin app) {
        app.get("/health", ctx -> ctx.json(Map.of("status", "ok")));

        app.post("/books", this::create);
        app.get("/books", this::list);
        app.get("/books/{id}", this::getOne);
        app.put("/books/{id}", this::update);
        app.delete("/books/{id}", this::delete);
    }

    void create(Context ctx) throws SQLException {
        Book book = ctx.bodyAsClass(Book.class);
        BookInputValidator.validateForCreate(book);
        Book saved = repository.create(book);
        ctx.status(HttpStatus.CREATED).json(saved);
    }

    void list(Context ctx) throws SQLException {
        String author = ctx.queryParam("author");
        ctx.json(repository.findAll(author));
    }

    void getOne(Context ctx) throws SQLException {
        long id = parseId(ctx);
        Book book = repository.findById(id)
                .orElseThrow(() -> new NotFoundException("book " + id + " not found"));
        ctx.json(book);
    }

    void update(Context ctx) throws SQLException {
        long id = parseId(ctx);
        Book book = ctx.bodyAsClass(Book.class);
        BookInputValidator.validateForUpdate(book);
        if (!repository.update(id, book)) {
            throw new NotFoundException("book " + id + " not found");
        }
        Book updated = repository.findById(id)
                .orElseThrow(() -> new NotFoundException("book " + id + " not found"));
        ctx.json(updated);
    }

    void delete(Context ctx) throws SQLException {
        long id = parseId(ctx);
        if (!repository.delete(id)) {
            throw new NotFoundException("book " + id + " not found");
        }
        ctx.status(HttpStatus.NO_CONTENT);
    }

    private static long parseId(Context ctx) {
        String raw = ctx.pathParam("id");
        try {
            return Long.parseLong(raw);
        } catch (NumberFormatException e) {
            throw new ValidationException("id must be a positive integer");
        }
    }
}
