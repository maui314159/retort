package com.example.books;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;

import java.io.IOException;

public class HealthHandler implements HttpHandler {
    @Override
    public void handle(HttpExchange exchange) throws IOException {
        try {
            if (!"GET".equalsIgnoreCase(exchange.getRequestMethod())) {
                HttpUtil.sendError(exchange, 405, "Method not allowed");
                return;
            }
            HttpUtil.sendJson(exchange, 200, java.util.Map.of("status", "ok"));
        } finally {
            exchange.close();
        }
    }
}
