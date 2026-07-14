package com.example.books;

import java.util.Map;

import io.javalin.http.HttpResponseException;
import io.javalin.http.HttpStatus;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Maps domain and framework exceptions to the right HTTP status code and
 * a stable JSON error envelope.
 */
public final class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    private GlobalExceptionHandler() {
    }

    public static void install(io.javalin.Javalin app) {
        app.exception(ValidationException.class, (e, ctx) -> {
            ctx.status(HttpStatus.BAD_REQUEST)
                    .json(Map.of("error", "validation_failed", "message", e.getMessage()));
        });
        app.exception(NotFoundException.class, (e, ctx) -> {
            ctx.status(HttpStatus.NOT_FOUND)
                    .json(Map.of("error", "not_found", "message", e.getMessage()));
        });
        app.exception(HttpResponseException.class, (e, ctx) -> {
            // Framework-thrown HTTP exceptions (NotFoundResponse, BadRequestResponse,
            // unknown-route 404, etc.). Javalin already picked the right status;
            // we just echo the message in our standard envelope.
            int status = e.getStatus() != 0 ? e.getStatus() : HttpStatus.INTERNAL_SERVER_ERROR.getCode();
            ctx.status(status)
                    .json(Map.of("error", status >= 500 ? "server_error" : "client_error",
                            "message", e.getMessage() == null ? "" : e.getMessage()));
        });
        app.exception(Exception.class, (e, ctx) -> {
            log.error("unhandled exception serving {} {}", ctx.method(), ctx.path(), e);
            ctx.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .json(Map.of("error", "server_error", "message", "internal error"));
        });
    }
}
