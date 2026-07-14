package com.example.books;

import java.nio.file.Files;
import java.nio.file.Path;

import io.javalin.Javalin;
import io.javalin.json.JavalinJackson;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;

/**
 * Process entry point.
 *
 * Boots a Javalin app wired to an on-disk SQLite database at
 * {@code BOOKS_DB} (default: {@code ./books.db}). All HTTP routing
 * lives in {@link BookController}; all error mapping lives in
 * {@link GlobalExceptionHandler}.
 */
public final class Application {

    private Application() {
    }

    public static void main(String[] args) {
        String jdbcUrl = resolveJdbcUrl();
        int port = resolvePort();
        Javalin app = bootstrap(jdbcUrl).start(port);
        Runtime.getRuntime().addShutdownHook(new Thread(app::stop, "books-api-shutdown"));
    }

    /**
     * Build and start a fully wired Javalin app against the given JDBC URL.
     * Exposed for tests and ad-hoc tooling.
     */
    public static Javalin bootstrap(String jdbcUrl) {
        Database database = new Database(jdbcUrl);
        try {
            ensureDatabaseDirectory(jdbcUrl);
            database.initializeSchema();
        } catch (Exception e) {
            throw new IllegalStateException("failed to initialise database at " + jdbcUrl, e);
        }
        BookRepository repository = new BookRepository(database);
        BookController controller = new BookController(repository);

        Javalin app = Javalin.create(config -> {
            config.jsonMapper(new JavalinJackson(buildObjectMapper(), false));
            config.showJavalinBanner = false;
        });
        GlobalExceptionHandler.install(app);
        controller.register(app);
        return app;
    }

    private static ObjectMapper buildObjectMapper() {
        ObjectMapper mapper = new ObjectMapper();
        mapper.registerModule(new JavaTimeModule());
        mapper.disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
        return mapper;
    }

    private static String resolveJdbcUrl() {
        String env = System.getenv("BOOKS_DB");
        if (env != null && !env.isBlank()) {
            return env.startsWith("jdbc:") ? env : "jdbc:sqlite:" + env;
        }
        return "jdbc:sqlite:books.db";
    }

    private static int resolvePort() {
        String env = System.getenv("PORT");
        if (env != null && !env.isBlank()) {
            try {
                return Integer.parseInt(env.trim());
            } catch (NumberFormatException ignored) {
                // fall through to default
            }
        }
        return 7000;
    }

    private static void ensureDatabaseDirectory(String jdbcUrl) throws java.io.IOException {
        // File-backed URLs (jdbc:sqlite:/path/to.db) may point at a parent
        // directory that does not exist yet. In-memory URLs (jdbc:sqlite::memory:)
        // and read-only URLs have no parent path component.
        if (!jdbcUrl.startsWith("jdbc:sqlite:")) {
            return;
        }
        String path = jdbcUrl.substring("jdbc:sqlite:".length());
        if (path.isBlank() || path.equals(":memory:")) {
            return;
        }
        Path parent = Path.of(path).toAbsolutePath().getParent();
        if (parent != null) {
            Files.createDirectories(parent);
        }
    }
}
