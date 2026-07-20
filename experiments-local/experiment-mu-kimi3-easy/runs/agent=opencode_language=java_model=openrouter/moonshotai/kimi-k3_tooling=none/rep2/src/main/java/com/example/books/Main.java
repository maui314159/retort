package com.example.books;

/**
 * Why: TASK.md requires a runnable service.
 * What: wires the SQLite repository to the HTTP server and starts it.
 * Configuration via environment: PORT (default 8080), DB_URL (default jdbc:sqlite:books.db).
 */
public class Main {

    public static void main(String[] args) throws Exception {
        int port = Integer.parseInt(System.getenv().getOrDefault("PORT", "8080"));
        String dbUrl = System.getenv().getOrDefault("DB_URL", "jdbc:sqlite:books.db");

        BookRepository repository = new BookRepository(dbUrl);
        BookApiServer api = new BookApiServer(port, repository);

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            api.stop();
            try {
                repository.close();
            } catch (Exception ignored) {
                // best-effort cleanup on shutdown
            }
        }));

        api.start();
        System.out.println("Book service listening on http://localhost:" + api.getPort());
    }
}
