package com.books;

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
 * SQLite-backed persistence for books. Each operation opens a short-lived
 * connection, which is the recommended pattern for the xerial SQLite driver.
 */
public class BookRepository {

    private final String jdbcUrl;

    public BookRepository(String dbPath) {
        this.jdbcUrl = "jdbc:sqlite:" + dbPath;
        initSchema();
    }

    private Connection connect() throws SQLException {
        return DriverManager.getConnection(jdbcUrl);
    }

    private void initSchema() {
        String sql = """
                CREATE TABLE IF NOT EXISTS books (
                    id     INTEGER PRIMARY KEY AUTOINCREMENT,
                    title  TEXT NOT NULL,
                    author TEXT NOT NULL,
                    year   INTEGER,
                    isbn   TEXT
                )
                """;
        try (Connection conn = connect(); Statement stmt = conn.createStatement()) {
            stmt.execute(sql);
        } catch (SQLException e) {
            throw new IllegalStateException("Failed to initialize database schema", e);
        }
    }

    /** Inserts the book and populates its generated id. */
    public Book create(Book book) {
        String sql = "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)";
        try (Connection conn = connect();
             PreparedStatement ps = conn.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS)) {
            bind(ps, book);
            ps.executeUpdate();
            try (ResultSet keys = ps.getGeneratedKeys()) {
                if (keys.next()) {
                    book.setId(keys.getLong(1));
                }
            }
            return book;
        } catch (SQLException e) {
            throw new IllegalStateException("Failed to create book", e);
        }
    }

    /** Lists all books, optionally filtered by exact author name. */
    public List<Book> findAll(String authorFilter) {
        boolean filter = authorFilter != null && !authorFilter.isBlank();
        String sql = "SELECT id, title, author, year, isbn FROM books"
                + (filter ? " WHERE author = ?" : "")
                + " ORDER BY id";
        List<Book> books = new ArrayList<>();
        try (Connection conn = connect(); PreparedStatement ps = conn.prepareStatement(sql)) {
            if (filter) {
                ps.setString(1, authorFilter);
            }
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    books.add(mapRow(rs));
                }
            }
        } catch (SQLException e) {
            throw new IllegalStateException("Failed to list books", e);
        }
        return books;
    }

    public Optional<Book> findById(long id) {
        String sql = "SELECT id, title, author, year, isbn FROM books WHERE id = ?";
        try (Connection conn = connect(); PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setLong(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                if (rs.next()) {
                    return Optional.of(mapRow(rs));
                }
                return Optional.empty();
            }
        } catch (SQLException e) {
            throw new IllegalStateException("Failed to find book " + id, e);
        }
    }

    /** Returns true if a row was updated (i.e. the id exists). */
    public boolean update(Book book) {
        String sql = "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?";
        try (Connection conn = connect(); PreparedStatement ps = conn.prepareStatement(sql)) {
            bind(ps, book);
            ps.setLong(5, book.getId());
            return ps.executeUpdate() > 0;
        } catch (SQLException e) {
            throw new IllegalStateException("Failed to update book " + book.getId(), e);
        }
    }

    /** Returns true if a row was deleted (i.e. the id exists). */
    public boolean delete(long id) {
        String sql = "DELETE FROM books WHERE id = ?";
        try (Connection conn = connect(); PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setLong(1, id);
            return ps.executeUpdate() > 0;
        } catch (SQLException e) {
            throw new IllegalStateException("Failed to delete book " + id, e);
        }
    }

    private static void bind(PreparedStatement ps, Book book) throws SQLException {
        ps.setString(1, book.getTitle());
        ps.setString(2, book.getAuthor());
        if (book.getYear() != null) {
            ps.setInt(3, book.getYear());
        } else {
            ps.setNull(3, java.sql.Types.INTEGER);
        }
        ps.setString(4, book.getIsbn());
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
}
