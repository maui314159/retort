package com.example.books;

import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.sql.SQLException;
import java.util.concurrent.Executors;

/**
 * Entry point and lifecycle for the Book Collection REST API.
 *
 * <p>Configuration via environment variables:
 * <ul>
 *   <li>{@code PORT} — listen port (default 8080)</li>
 *   <li>{@code BOOKS_DB} — SQLite file path (default {@code books.db})</li>
 * </ul>
 */
public class BookApiServer {

    private final HttpServer server;
    private final BookRepository repo;

    public BookApiServer(int port, BookRepository repo) throws IOException {
        this.repo = repo;
        this.server = HttpServer.create(new InetSocketAddress(port), 0);
        server.createContext("/books", new BookHandler(repo));
        server.createContext("/health", new HealthHandler());
        server.setExecutor(Executors.newFixedThreadPool(4));
    }

    public void start() {
        server.start();
    }

    public void stop() {
        server.stop(0);
        repo.close();
    }

    /** Effective port (useful when bound to port 0). */
    public int getPort() {
        return server.getAddress().getPort();
    }

    public BookRepository getRepo() {
        return repo;
    }

    public static void main(String[] args) throws IOException, SQLException {
        int port = Integer.parseInt(System.getenv().getOrDefault("PORT", "8080"));
        String dbPath = System.getenv().getOrDefault("BOOKS_DB", "books.db");

        BookApiServer api = new BookApiServer(port, BookRepository.forFile(dbPath));
        Runtime.getRuntime().addShutdownHook(new Thread(api::stop));
        api.start();
        System.out.println("Book API listening on http://localhost:" + api.getPort());
        System.out.println("SQLite database: " + dbPath);
    }
}
