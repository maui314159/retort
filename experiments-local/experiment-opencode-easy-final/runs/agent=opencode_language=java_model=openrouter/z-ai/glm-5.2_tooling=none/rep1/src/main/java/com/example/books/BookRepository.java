package com.example.books;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

public class BookRepository {

    private static final String SCHEMA = """
            CREATE TABLE IF NOT EXISTS books (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year  INTEGER,
                isbn  TEXT
            )
            """;

    private final String jdbcUrl;

    public BookRepository(String dbPath) {
        this.jdbcUrl = "jdbc:sqlite:" + dbPath;
        initSchema();
    }

    private Connection open() throws SQLException {
        return DriverManager.getConnection(jdbcUrl);
    }

    private void initSchema() {
        try (Connection conn = open();
             Statement stmt = conn.createStatement()) {
            stmt.execute(SCHEMA);
        } catch (SQLException e) {
            throw new RuntimeException("Failed to initialize database schema", e);
        }
    }

    public Book save(Book book) {
        String sql = "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)";
        try (Connection conn = open();
             PreparedStatement ps = conn.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS)) {
            ps.setString(1, book.title());
            ps.setString(2, book.author());
            if (book.year() != null) {
                ps.setInt(3, book.year());
            } else {
                ps.setNull(3, java.sql.Types.INTEGER);
            }
            ps.setString(4, book.isbn());
            ps.executeUpdate();
            try (ResultSet keys = ps.getGeneratedKeys()) {
                if (keys.next()) {
                    return book.withId(keys.getLong(1));
                }
            }
            throw new SQLException("Failed to retrieve generated id");
        } catch (SQLException e) {
            throw new RuntimeException("Failed to save book", e);
        }
    }

    public List<Book> findAll(String authorFilter) {
        String sql;
        if (authorFilter != null && !authorFilter.isBlank()) {
            sql = "SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id";
        } else {
            sql = "SELECT id, title, author, year, isbn FROM books ORDER BY id";
        }
        List<Book> result = new ArrayList<>();
        try (Connection conn = open();
             PreparedStatement ps = conn.prepareStatement(sql)) {
            if (authorFilter != null && !authorFilter.isBlank()) {
                ps.setString(1, authorFilter);
            }
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    result.add(mapRow(rs));
                }
            }
        } catch (SQLException e) {
            throw new RuntimeException("Failed to list books", e);
        }
        return result;
    }

    public Optional<Book> findById(Long id) {
        String sql = "SELECT id, title, author, year, isbn FROM books WHERE id = ?";
        try (Connection conn = open();
             PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setLong(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                if (rs.next()) {
                    return Optional.of(mapRow(rs));
                }
            }
        } catch (SQLException e) {
            throw new RuntimeException("Failed to find book by id", e);
        }
        return Optional.empty();
    }

    public boolean update(Long id, Book book) {
        String sql = "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?";
        try (Connection conn = open();
             PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setString(1, book.title());
            ps.setString(2, book.author());
            if (book.year() != null) {
                ps.setInt(3, book.year());
            } else {
                ps.setNull(3, java.sql.Types.INTEGER);
            }
            ps.setString(4, book.isbn());
            ps.setLong(5, id);
            return ps.executeUpdate() > 0;
        } catch (SQLException e) {
            throw new RuntimeException("Failed to update book", e);
        }
    }

    public boolean delete(Long id) {
        String sql = "DELETE FROM books WHERE id = ?";
        try (Connection conn = open();
             PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setLong(1, id);
            return ps.executeUpdate() > 0;
        } catch (SQLException e) {
            throw new RuntimeException("Failed to delete book", e);
        }
    }

    private Book mapRow(ResultSet rs) throws SQLException {
        Integer year = rs.getObject("year", Integer.class);
        return new Book(
                rs.getLong("id"),
                rs.getString("title"),
                rs.getString("author"),
                year,
                rs.getString("isbn")
        );
    }
}
