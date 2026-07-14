package com.example.books;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.Optional;

/**
 * CRUD access for {@link Book} records backed by SQLite.
 *
 * The repository owns no connection state: each method opens and closes its
 * own connection through the {@link Database} factory. SQLite supports
 * concurrent readers, and the embedded engine does not need pooling for
 * the throughput of a small REST service.
 */
public final class BookRepository {

    private final Database database;

    public BookRepository(Database database) {
        this.database = Objects.requireNonNull(database, "database");
    }

    /**
     * Insert a new book and return it with the generated id populated.
     */
    public Book create(Book book) throws SQLException {
        String sql = "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)";
        try (Connection conn = database.openConnection();
             PreparedStatement ps = conn.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS)) {
            ps.setString(1, book.getTitle());
            ps.setString(2, book.getAuthor());
            setNullableInt(ps, 3, book.getYear());
            ps.setString(4, book.getIsbn());
            ps.executeUpdate();
            try (ResultSet keys = ps.getGeneratedKeys()) {
                if (keys.next()) {
                    book.setId(keys.getLong(1));
                }
            }
        }
        return book;
    }

    /**
     * List books, optionally filtered by author (case-insensitive exact match).
     */
    public List<Book> findAll(String authorFilter) throws SQLException {
        StringBuilder sql = new StringBuilder(
                "SELECT id, title, author, year, isbn FROM books");
        if (authorFilter != null && !authorFilter.isBlank()) {
            sql.append(" WHERE LOWER(author) = LOWER(?)");
        }
        sql.append(" ORDER BY id");

        try (Connection conn = database.openConnection();
             PreparedStatement ps = conn.prepareStatement(sql.toString())) {
            if (authorFilter != null && !authorFilter.isBlank()) {
                ps.setString(1, authorFilter.trim());
            }
            try (ResultSet rs = ps.executeQuery()) {
                List<Book> out = new ArrayList<>();
                while (rs.next()) {
                    out.add(mapRow(rs));
                }
                return out;
            }
        }
    }

    public Optional<Book> findById(long id) throws SQLException {
        String sql = "SELECT id, title, author, year, isbn FROM books WHERE id = ?";
        try (Connection conn = database.openConnection();
             PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setLong(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                if (rs.next()) {
                    return Optional.of(mapRow(rs));
                }
                return Optional.empty();
            }
        }
    }

    public boolean update(long id, Book book) throws SQLException {
        String sql = "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?";
        try (Connection conn = database.openConnection();
             PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setString(1, book.getTitle());
            ps.setString(2, book.getAuthor());
            setNullableInt(ps, 3, book.getYear());
            ps.setString(4, book.getIsbn());
            ps.setLong(5, id);
            return ps.executeUpdate() > 0;
        }
    }

    public boolean delete(long id) throws SQLException {
        String sql = "DELETE FROM books WHERE id = ?";
        try (Connection conn = database.openConnection();
             PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setLong(1, id);
            return ps.executeUpdate() > 0;
        }
    }

    private static Book mapRow(ResultSet rs) throws SQLException {
        Book b = new Book();
        b.setId(rs.getLong("id"));
        b.setTitle(rs.getString("title"));
        b.setAuthor(rs.getString("author"));
        int year = rs.getInt("year");
        b.setYear(rs.wasNull() ? null : year);
        b.setIsbn(rs.getString("isbn"));
        return b;
    }

    private static void setNullableInt(PreparedStatement ps, int index, Integer value) throws SQLException {
        if (value == null) {
            ps.setNull(index, java.sql.Types.INTEGER);
        } else {
            ps.setInt(index, value);
        }
    }
}
