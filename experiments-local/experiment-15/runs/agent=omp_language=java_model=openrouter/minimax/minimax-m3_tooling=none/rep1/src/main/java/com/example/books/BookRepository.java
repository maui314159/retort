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

/**
 * SQLite-backed book store. All operations synchronize on the connection so
 * SQLite's single-writer model is respected under Javalin's thread pool.
 */
public final class BookRepository implements AutoCloseable {

    private final Connection connection;

    public BookRepository(String jdbcUrl) {
        try {
            this.connection = DriverManager.getConnection(jdbcUrl);
            try (Statement st = connection.createStatement()) {
                st.executeUpdate("""
                        CREATE TABLE IF NOT EXISTS books (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            title TEXT NOT NULL,
                            author TEXT NOT NULL,
                            year INTEGER,
                            isbn TEXT
                        )
                        """);
            }
        } catch (SQLException e) {
            throw new IllegalStateException("Failed to initialize repository at " + jdbcUrl, e);
        }
    }

    public Book create(Book book) {
        String sql = "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)";
        synchronized (connection) {
            try (PreparedStatement ps = connection.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS)) {
                ps.setString(1, book.getTitle());
                ps.setString(2, book.getAuthor());
                if (book.getYear() != null) {
                    ps.setInt(3, book.getYear());
                } else {
                    ps.setNull(3, java.sql.Types.INTEGER);
                }
                ps.setString(4, book.getIsbn());
                ps.executeUpdate();
                try (ResultSet keys = ps.getGeneratedKeys()) {
                    if (keys.next()) {
                        return book.withId(keys.getLong(1));
                    }
                    throw new IllegalStateException("Insert did not return an id");
                }
            } catch (SQLException e) {
                throw new IllegalStateException("Failed to create book", e);
            }
        }
    }

    public List<Book> findAll(String authorFilter) {
        StringBuilder sql = new StringBuilder("SELECT id, title, author, year, isbn FROM books");
        boolean hasFilter = authorFilter != null && !authorFilter.isBlank();
        if (hasFilter) {
            sql.append(" WHERE author = ?");
        }
        sql.append(" ORDER BY id");
        synchronized (connection) {
            try (PreparedStatement ps = connection.prepareStatement(sql.toString())) {
                if (hasFilter) {
                    ps.setString(1, authorFilter);
                }
                try (ResultSet rs = ps.executeQuery()) {
                    List<Book> out = new ArrayList<>();
                    while (rs.next()) {
                        out.add(map(rs));
                    }
                    return out;
                }
            } catch (SQLException e) {
                throw new IllegalStateException("Failed to list books", e);
            }
        }
    }

    public Optional<Book> findById(long id) {
        String sql = "SELECT id, title, author, year, isbn FROM books WHERE id = ?";
        synchronized (connection) {
            try (PreparedStatement ps = connection.prepareStatement(sql)) {
                ps.setLong(1, id);
                try (ResultSet rs = ps.executeQuery()) {
                    if (rs.next()) {
                        return Optional.of(map(rs));
                    }
                    return Optional.empty();
                }
            } catch (SQLException e) {
                throw new IllegalStateException("Failed to fetch book " + id, e);
            }
        }
    }

    /**
     * Updates the book identified by {@code id}. Returns the updated row, or
     * empty if no such book exists.
     */
    public Optional<Book> update(long id, Book book) {
        String sql = "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?";
        synchronized (connection) {
            try (PreparedStatement ps = connection.prepareStatement(sql)) {
                ps.setString(1, book.getTitle());
                ps.setString(2, book.getAuthor());
                if (book.getYear() != null) {
                    ps.setInt(3, book.getYear());
                } else {
                    ps.setNull(3, java.sql.Types.INTEGER);
                }
                ps.setString(4, book.getIsbn());
                ps.setLong(5, id);
                int rows = ps.executeUpdate();
                if (rows == 0) {
                    return Optional.empty();
                }
                return findById(id);
            } catch (SQLException e) {
                throw new IllegalStateException("Failed to update book " + id, e);
            }
        }
    }

    public boolean delete(long id) {
        String sql = "DELETE FROM books WHERE id = ?";
        synchronized (connection) {
            try (PreparedStatement ps = connection.prepareStatement(sql)) {
                ps.setLong(1, id);
                return ps.executeUpdate() > 0;
            } catch (SQLException e) {
                throw new IllegalStateException("Failed to delete book " + id, e);
            }
        }
    }

    private static Book map(ResultSet rs) throws SQLException {
        int year = rs.getInt("year");
        Integer yearBox = rs.wasNull() ? null : year;
        return new Book(
                rs.getLong("id"),
                rs.getString("title"),
                rs.getString("author"),
                yearBox,
                rs.getString("isbn"));
    }

    @Override
    public void close() {
        try {
            connection.close();
        } catch (SQLException e) {
            // best-effort
        }
    }
}
