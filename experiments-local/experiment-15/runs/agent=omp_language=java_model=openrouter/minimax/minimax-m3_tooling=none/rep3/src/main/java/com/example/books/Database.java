package com.example.books;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.Objects;
import java.util.stream.Collectors;

/**
 * Thin factory for opening SQLite connections and applying the schema.
 *
 * Each call to {@link #openConnection()} returns a fresh connection; SQLite
 * connections are cheap and the embedded engine is happy to handle many of
 * them concurrently. Callers are responsible for closing connections (try-
 * with-resources is the right idiom).
 */
public final class Database {

    private final String jdbcUrl;

    public Database(String jdbcUrl) {
        this.jdbcUrl = Objects.requireNonNull(jdbcUrl, "jdbcUrl");
    }

    public Connection openConnection() throws SQLException {
        return DriverManager.getConnection(jdbcUrl);
    }

    /**
     * Open a connection and run the bundled {@code schema.sql} against it.
     * Used at startup and from tests to provision a fresh database.
     */
    public void initializeSchema() throws SQLException, IOException {
        try (Connection conn = openConnection();
             Statement stmt = conn.createStatement()) {
            stmt.executeUpdate(loadSchema());
        }
    }

    private static String loadSchema() throws IOException {
        ClassLoader cl = Thread.currentThread().getContextClassLoader();
        if (cl == null) {
            cl = Database.class.getClassLoader();
        }
        try (InputStream in = cl.getResourceAsStream("schema.sql")) {
            if (in == null) {
                throw new IOException("schema.sql not found on classpath");
            }
            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(in, StandardCharsets.UTF_8))) {
                return reader.lines().collect(Collectors.joining("\n"));
            }
        }
    }
}
