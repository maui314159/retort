package com.example.bookstore;

import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.sql.SQLException;

public final class Main {

    public static final int DEFAULT_PORT = 8080;
    public static final String DEFAULT_DB_URL = "jdbc:sqlite:books.db";

    public static void main(String[] args) throws IOException, SQLException {
        int port = envInt("PORT", DEFAULT_PORT);
        String dbUrl = envOr("DB_URL", DEFAULT_DB_URL);

        BookDao dao = new BookDao(dbUrl);
        dao.init();

        HttpServer server = HttpServer.create(new InetSocketAddress(port), 0);
        server.createContext("/", new BookStoreHandler(dao));
        server.setExecutor(java.util.concurrent.Executors.newFixedThreadPool(8));
        server.start();

        System.out.println("Bookstore REST API listening on http://localhost:" + port);
        System.out.println("Using database: " + dbUrl);
        System.out.println("Press Ctrl+C to stop.");
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            System.out.println("Stopping...");
            server.stop(0);
        }));
    }

    private static int envInt(String name, int fallback) {
        String v = System.getenv(name);
        if (v == null || v.isBlank()) return fallback;
        try { return Integer.parseInt(v.trim()); } catch (NumberFormatException e) { return fallback; }
    }

    private static String envOr(String name, String fallback) {
        String v = System.getenv(name);
        return (v == null || v.isBlank()) ? fallback : v;
    }
}
