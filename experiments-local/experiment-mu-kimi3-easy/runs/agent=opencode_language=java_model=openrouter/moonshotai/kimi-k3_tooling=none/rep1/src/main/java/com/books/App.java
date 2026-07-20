package com.books;

/**
 * Application entry point. Configuration via environment variables:
 * {@code PORT} (default 8080) and {@code BOOKS_DB} (default "books.db").
 */
public class App {

    public static void main(String[] args) throws Exception {
        int port = Integer.parseInt(System.getenv().getOrDefault("PORT", "8080"));
        String dbPath = System.getenv().getOrDefault("BOOKS_DB", "books.db");

        BookServer server = new BookServer(port, dbPath);
        Runtime.getRuntime().addShutdownHook(new Thread(server::stop));
        server.start();

        System.out.printf("Book service listening on http://localhost:%d (db: %s)%n", server.getPort(), dbPath);
        Thread.currentThread().join();
    }
}
