package com.example.books;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;

import java.io.IOException;
import java.util.Map;

/** Health check: GET /health returns {@code 200 {"status":"ok"}}. */
public class HealthHandler implements HttpHandler {

    @Override
    public void handle(HttpExchange exchange) throws IOException {
        try {
            if ("GET".equals(exchange.getRequestMethod())) {
                BookHandler.sendJson(exchange, 200, Map.of("status", "ok"));
            } else {
                BookHandler.sendError(exchange, 405, "Method not allowed");
            }
        } finally {
            exchange.close();
        }
    }
}
