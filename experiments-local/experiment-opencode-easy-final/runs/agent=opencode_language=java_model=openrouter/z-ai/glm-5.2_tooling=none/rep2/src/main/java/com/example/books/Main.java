package com.example.books;

import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.sql.SQLException;

public class Main {

    public static void main(String[] args) throws IOException, SQLException {
        int port = envPort();
        String dbPath = envOr("BOOKS_DB_PATH", "books.db");
        BookRepository repository = new BookRepository(dbPath);
        HttpServer server = HttpServer.create(new InetSocketAddress(port), 0);
        server.createContext("/health", new HealthHandler());
        server.createContext("/books", new BookHandler(repository));
        server.setExecutor(java.util.concurrent.Executors.newFixedThreadPool(8));
        server.start();
        System.out.println("Books API listening on http://localhost:" + port);
        System.out.println("SQLite database at: " + dbPath);
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            server.stop(0);
            try { repository.close(); } catch (SQLException e) { /* ignore on shutdown */ }
        }));
    }

    static int envPort() {
        String p = System.getenv("PORT");
        if (p == null || p.isBlank()) return 8080;
        try { return Integer.parseInt(p); } catch (NumberFormatException e) { return 8080; }
    }

    static String envOr(String key, String def) {
        String v = System.getenv(key);
        return (v == null || v.isBlank()) ? def : v;
    }
}
