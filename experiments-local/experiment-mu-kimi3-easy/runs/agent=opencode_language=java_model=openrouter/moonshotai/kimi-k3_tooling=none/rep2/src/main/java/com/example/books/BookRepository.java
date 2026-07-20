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
 * Why: TASK.md requires storing books in SQLite (embedded DB).
 * What: JDBC-backed CRUD over a single shared connection. Methods are synchronized
 * because the HTTP server dispatches requests from a thread pool and one JDBC
 * connection must not be used concurrently.
 */
public class BookRepository implements AutoCloseable {

    private final Connection connection;

    public BookRepository(String jdbcUrl) throws SQLException {
        this.connection = DriverManager.getConnection(jdbcUrl);
        try (Statement st = connection.createStatement()) {
            st.executeUpdate("CREATE TABLE IF NOT EXISTS books ("
                    + "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                    + "title TEXT NOT NULL, "
                    + "author TEXT NOT NULL, "
                    + "year INTEGER, "
                    + "isbn TEXT)");
        }
    }

    public synchronized Book create(Book book) throws SQLException {
        String sql = "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)";
        try (PreparedStatement ps = connection.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS)) {
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
                book.setId(keys.getInt(1));
            }
        }
        return book;
    }

    public synchronized List<Book> findAll(String authorFilter) throws SQLException {
        String sql = "SELECT id, title, author, year, isbn FROM books"
                + (authorFilter != null ? " WHERE author = ?" : "")
                + " ORDER BY id";
        List<Book> books = new ArrayList<>();
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            if (authorFilter != null) {
                ps.setString(1, authorFilter);
            }
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    books.add(map(rs));
                }
            }
        }
        return books;
    }

    public synchronized Optional<Book> findById(int id) throws SQLException {
        try (PreparedStatement ps = connection.prepareStatement(
                "SELECT id, title, author, year, isbn FROM books WHERE id = ?")) {
            ps.setInt(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() ? Optional.of(map(rs)) : Optional.empty();
            }
        }
    }

    public synchronized boolean update(Book book) throws SQLException {
        try (PreparedStatement ps = connection.prepareStatement(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?")) {
            ps.setString(1, book.getTitle());
            ps.setString(2, book.getAuthor());
            if (book.getYear() != null) {
                ps.setInt(3, book.getYear());
            } else {
                ps.setNull(3, Types.INTEGER);
            }
            ps.setString(4, book.getIsbn());
            ps.setInt(5, book.getId());
            return ps.executeUpdate() > 0;
        }
    }

    public synchronized boolean delete(int id) throws SQLException {
        try (PreparedStatement ps = connection.prepareStatement("DELETE FROM books WHERE id = ?")) {
            ps.setInt(1, id);
            return ps.executeUpdate() > 0;
        }
    }

    private static Book map(ResultSet rs) throws SQLException {
        Book book = new Book();
        book.setId(rs.getInt("id"));
        book.setTitle(rs.getString("title"));
        book.setAuthor(rs.getString("author"));
        int year = rs.getInt("year");
        book.setYear(rs.wasNull() ? null : year);
        book.setIsbn(rs.getString("isbn"));
        return book;
    }

    @Override
    public void close() throws SQLException {
        connection.close();
    }
}
