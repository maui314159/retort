package com.example.books;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import io.javalin.http.Context;
import io.javalin.http.HttpStatus;

import java.util.Map;

public class BookController {

    private final BookRepository repository;
    private final ObjectMapper mapper;

    public BookController(BookRepository repository, ObjectMapper mapper) {
        this.repository = repository;
        this.mapper = mapper;
    }

    public void create(Context ctx) {
        Book payload = parseBody(ctx, true);
        Book saved = repository.save(payload);
        ctx.json(saved).status(HttpStatus.CREATED);
    }

    public void list(Context ctx) {
        String author = ctx.queryParam("author");
        ctx.json(repository.findAll(author)).status(HttpStatus.OK);
    }

    public void getOne(Context ctx) {
        Long id = parseId(ctx);
        Book book = repository.findById(id)
                .orElseThrow(() -> new NotFoundException("Book not found: " + id));
        ctx.json(book).status(HttpStatus.OK);
    }

    public void update(Context ctx) {
        Long id = parseId(ctx);
        Book payload = parseBody(ctx, true);
        boolean updated = repository.update(id, payload);
        if (!updated) {
            throw new NotFoundException("Book not found: " + id);
        }
        ctx.json(payload.withId(id)).status(HttpStatus.OK);
    }

    public void delete(Context ctx) {
        Long id = parseId(ctx);
        boolean deleted = repository.delete(id);
        if (!deleted) {
            throw new NotFoundException("Book not found: " + id);
        }
        ctx.status(HttpStatus.NO_CONTENT);
    }

    public void health(Context ctx) {
        ObjectNode body = mapper.createObjectNode();
        body.put("status", "ok");
        ctx.json(body).status(HttpStatus.OK);
    }

    private Long parseId(Context ctx) {
        try {
            return Long.parseLong(ctx.pathParam("id"));
        } catch (NumberFormatException e) {
            throw new ValidationException("Invalid id: must be a number");
        }
    }

    private Book parseBody(Context ctx, boolean requireTitleAndAuthor) {
        Book payload;
        try {
            payload = ctx.bodyAsClass(Book.class);
        } catch (Exception e) {
            throw new ValidationException("Request body is not valid JSON for a book");
        }
        if (payload == null) {
            throw new ValidationException("Request body is required");
        }
        if (requireTitleAndAuthor) {
            if (payload.title() == null || payload.title().isBlank()) {
                throw new ValidationException("title is required");
            }
            if (payload.author() == null || payload.author().isBlank()) {
                throw new ValidationException("author is required");
            }
        }
        if (payload.year() != null && (payload.year() < 0 || payload.year() > 9999)) {
            throw new ValidationException("year must be between 0 and 9999");
        }
        return payload;
    }

    public static class NotFoundException extends RuntimeException {
        public NotFoundException(String message) {
            super(message);
        }
    }

    static Map<String, String> errorBody(String message) {
        return Map.of("error", message);
    }
}
