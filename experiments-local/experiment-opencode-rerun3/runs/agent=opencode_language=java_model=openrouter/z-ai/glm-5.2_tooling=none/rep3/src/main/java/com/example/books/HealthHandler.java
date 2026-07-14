package com.example.books;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;

import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;

public class HealthHandler implements HttpHandler {
    @Override
    public void handle(HttpExchange exchange) throws IOException {
        if (!"GET".equals(exchange.getRequestMethod())) {
            exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
            byte[] err = "{\"error\":\"Method not allowed\"}".getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(405, err.length);
            try (OutputStream os = exchange.getResponseBody()) {
                os.write(err);
            }
            exchange.close();
            return;
        }
        String body = "{\"status\":\"ok\"}";
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        exchange.sendResponseHeaders(200, bytes.length);
        try (OutputStream os = exchange.getResponseBody()) {
            os.write(bytes);
        }
        exchange.close();
    }
}
