package com.example;

import java.io.IOException;

public class Main {
    public static void main(String[] args) throws IOException {
        String portEnv = System.getenv().getOrDefault("PORT", "8080");
        int port = Integer.parseInt(portEnv);
        String dbUrl = System.getenv().getOrDefault("DB_URL", "jdbc:sqlite:books.db");

        try (BookService service = new BookService(dbUrl)) {
            Router router = new Router(service, port);
            router.start();
            System.out.println("Books API listening on http://localhost:" + port + " (db=" + dbUrl + ")");
            Runtime.getRuntime().addShutdownHook(new Thread(() -> {
                System.out.println("shutting down...");
                router.close();
            }));
            Thread.currentThread().join();
        } catch (Exception e) {
            System.err.println("failed to start server: " + e.getMessage());
            System.exit(1);
        }
    }
}
