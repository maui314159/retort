package com.example.books;

import io.javalin.Javalin;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Entry point. Boots a Javalin server backed by a SQLite book repository.
 *
 * <p>Usage:
 * <pre>
 *   java -jar books-api.jar [port] [db-path]
 *   # defaults: port=7000, db-path=./books.db
 * </pre>
 */
public final class App {

    private static final Logger log = LoggerFactory.getLogger(App.class);

    private App() {
    }

    public static void main(String[] args) {
        int port = args.length > 0 ? parsePort(args[0]) : 7000;
        String dbPath = args.length > 1 ? args[1] : "books.db";
        String jdbcUrl = ":memory:".equals(dbPath)
                ? "jdbc:sqlite::memory:"
                : "jdbc:sqlite:" + dbPath;

        BookRepository repo = new BookRepository(jdbcUrl);
        Javalin app = new BookController(repo).createApp();
        app.start(port);
        log.info("books-api listening on http://localhost:{} (db={})", port, jdbcUrl);

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            log.info("shutting down");
            app.stop();
            repo.close();
        }, "books-api-shutdown"));
    }

    private static int parsePort(String raw) {
        try {
            int port = Integer.parseInt(raw);
            if (port < 1 || port > 65535) {
                throw new NumberFormatException("port out of range");
            }
            return port;
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("Invalid port: " + raw, e);
        }
    }
}
