package com.example.books;

import com.fasterxml.jackson.core.JsonProcessingException;
import io.javalin.Javalin;
import io.javalin.http.BadRequestResponse;
import io.javalin.http.Context;
import io.javalin.http.HttpStatus;
import io.javalin.json.JavalinJackson;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Wires the HTTP routes for the books resource onto a Javalin app.
 */
public final class BookController {

    private static final Logger log = LoggerFactory.getLogger(BookController.class);

    private final BookRepository repository;

    public BookController(BookRepository repository) {
        this.repository = repository;
    }

    /**
     * Builds a fully-configured Javalin app that uses this controller's
     * repository. Tests and {@link App#main(String[])} both call this; the
     * port is chosen by the caller via {@link Javalin#start()}.
     */
    public Javalin createApp() {
        Javalin app = Javalin.create(config -> {
            config.jsonMapper(new JavalinJackson());
            config.showJavalinBanner = false;
        });
        app.events(event -> event.serverStarting(() -> log.info("Starting books API")));
        app.exception(BadRequestResponse.class, (ex, ctx) -> {
            String message = ex.getMessage() != null ? ex.getMessage() : "bad request";
            ctx.status(HttpStatus.BAD_REQUEST).json(Map.of("error", message));
        });
        app.exception(JsonProcessingException.class, (ex, ctx) -> {
            String detail = ex.getOriginalMessage() != null ? ex.getOriginalMessage() : "malformed JSON";
            ctx.status(HttpStatus.BAD_REQUEST).json(Map.of("error", "malformed JSON: " + detail));
        });
        app.exception(Exception.class, (ex, ctx) -> {
            log.error("Unhandled error on {} {}", ctx.method(), ctx.path(), ex);
            ctx.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .json(Map.of("error", "internal server error"));
        });
        app.get("/health", this::health);
        app.get("/books", this::list);
        app.get("/books/{id}", this::getOne);
        app.post("/books", this::create);
        app.put("/books/{id}", this::update);
        app.delete("/books/{id}", this::delete);
        return app;
    }

    private void health(Context ctx) {
        ctx.json(Map.of("status", "ok"));
    }

    private void list(Context ctx) {
        String author = ctx.queryParam("author");
        ctx.json(repository.findAll(author));
    }

    private void getOne(Context ctx) {
        long id = parseId(ctx);
        if (id < 0) {
            return;
        }
        repository.findById(id).ifPresentOrElse(
                ctx::json,
                () -> notFound(ctx, "Book " + id + " not found"));
    }

    private void create(Context ctx) {
        BookInput input = ctx.bodyAsClass(BookInput.class);
        List<String> errors = input.validate();
        if (!errors.isEmpty()) {
            validationError(ctx, errors);
            return;
        }
        Book toCreate = new Book(null, input.title(), input.author(), input.year(), input.isbn());
        Book saved = repository.create(toCreate);
        ctx.status(HttpStatus.CREATED).json(saved);
    }

    private void update(Context ctx) {
        long id = parseId(ctx);
        if (id < 0) {
            return;
        }
        BookInput input = ctx.bodyAsClass(BookInput.class);
        List<String> errors = input.validate();
        if (!errors.isEmpty()) {
            validationError(ctx, errors);
            return;
        }
        Book replacement = new Book(null, input.title(), input.author(), input.year(), input.isbn());
        repository.update(id, replacement).ifPresentOrElse(
                ctx::json,
                () -> notFound(ctx, "Book " + id + " not found"));
    }

    private void delete(Context ctx) {
        long id = parseId(ctx);
        if (id < 0) {
            return;
        }
        if (repository.delete(id)) {
            ctx.status(HttpStatus.NO_CONTENT);
        } else {
            notFound(ctx, "Book " + id + " not found");
        }
    }

    private long parseId(Context ctx) {
        String raw = ctx.pathParam("id");
        try {
            long id = Long.parseLong(raw);
            if (id <= 0) {
                badRequest(ctx, "id must be a positive integer");
                return -1;
            }
            return id;
        } catch (NumberFormatException e) {
            badRequest(ctx, "id must be a positive integer");
            return -1;
        }
    }

    private void badRequest(Context ctx, String message) {
        ctx.status(HttpStatus.BAD_REQUEST).json(Map.of("error", message));
    }

    private void notFound(Context ctx, String message) {
        ctx.status(HttpStatus.NOT_FOUND).json(Map.of("error", message));
    }

    private void validationError(Context ctx, List<String> errors) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("error", "validation failed");
        body.put("details", errors);
        ctx.status(HttpStatus.BAD_REQUEST).json(body);
    }

    /**
     * Validated request body for create/update.
     */
    public record BookInput(String title, String author, Integer year, String isbn) {

        public List<String> validate() {
            List<String> errors = new ArrayList<>();
            if (title == null || title.isBlank()) {
                errors.add("title is required");
            }
            if (author == null || author.isBlank()) {
                errors.add("author is required");
            }
            return errors;
        }
    }
}
