package com.example.books;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.sql.Types;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

/**
 * SQLite-backed persistence for books. A single shared connection is used and
 * all operations are synchronized, which is sufficient for this service's
 * embedded, single-process deployment.
 */
public class BookRepository implements AutoCloseable {

    private final Connection conn;

    public BookRepository(String jdbcUrl) throws SQLException {
        this.conn = DriverManager.getConnection(jdbcUrl);
        try (Statement st = conn.createStatement()) {
            st.execute("CREATE TABLE IF NOT EXISTS books ("
                    + "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                    + "title TEXT NOT NULL, "
                    + "author TEXT NOT NULL, "
                    + "year INTEGER, "
                    + "isbn TEXT)");
        }
    }

    public static BookRepository forFile(String path) throws SQLException {
        return new BookRepository("jdbc:sqlite:" + path);
    }

    public synchronized Book create(Book book) throws SQLException {
        String sql = "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)";
        try (PreparedStatement ps = conn.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS)) {
            ps.setString(1, book.getTitle());
            ps.setString(2, book.getAuthor());
            if (book.getYear() != null) {
                ps.setInt(3, book.getYear());
            } else {
                ps.setNull(3, Types.INTEGER);
            }
            ps.setString(4, book.getIsbn());
            ps.executeUpdate();
            try (ResultSet keys = ps.getGeneratedKeys()) {
                keys.next();
                book.setId(keys.getLong(1));
            }
        }
        return book;
    }

    /** Returns all books, optionally filtered by exact (case-insensitive) author. */
    public synchronized List<Book> findAll(String authorFilter) throws SQLException {
        List<Book> books = new ArrayList<>();
        boolean filter = authorFilter != null && !authorFilter.isBlank();
        String sql = "SELECT id, title, author, year, isbn FROM books"
                + (filter ? " WHERE LOWER(author) = LOWER(?)" : "")
                + " ORDER BY id";
        try (PreparedStatement ps = conn.prepareStatement(sql)) {
            if (filter) {
                ps.setString(1, authorFilter);
            }
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    books.add(mapRow(rs));
                }
            }
        }
        return books;
    }

    public synchronized Optional<Book> findById(long id) throws SQLException {
        try (PreparedStatement ps = conn.prepareStatement(
                "SELECT id, title, author, year, isbn FROM books WHERE id = ?")) {
            ps.setLong(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                if (rs.next()) {
                    return Optional.of(mapRow(rs));
                }
            }
        }
        return Optional.empty();
    }

    /** @return true if a row with the given id existed and was updated. */
    public synchronized boolean update(long id, Book book) throws SQLException {
        String sql = "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?";
        try (PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setString(1, book.getTitle());
            ps.setString(2, book.getAuthor());
            if (book.getYear() != null) {
                ps.setInt(3, book.getYear());
            } else {
                ps.setNull(3, Types.INTEGER);
            }
            ps.setString(4, book.getIsbn());
            ps.setLong(5, id);
            return ps.executeUpdate() > 0;
        }
    }

    /** @return true if a row with the given id existed and was deleted. */
    public synchronized boolean delete(long id) throws SQLException {
        try (PreparedStatement ps = conn.prepareStatement("DELETE FROM books WHERE id = ?")) {
            ps.setLong(1, id);
            return ps.executeUpdate() > 0;
        }
    }

    /** Removes every book. Intended for tests. */
    public synchronized void deleteAll() throws SQLException {
        try (Statement st = conn.createStatement()) {
            st.executeUpdate("DELETE FROM books");
        }
    }

    private static Book mapRow(ResultSet rs) throws SQLException {
        Book book = new Book();
        book.setId(rs.getLong("id"));
        book.setTitle(rs.getString("title"));
        book.setAuthor(rs.getString("author"));
        int year = rs.getInt("year");
        book.setYear(rs.wasNull() ? null : year);
        book.setIsbn(rs.getString("isbn"));
        return book;
    }

    @Override
    public void close() {
        try {
            conn.close();
        } catch (SQLException ignored) {
            // nothing sensible to do on shutdown
        }
    }
}
