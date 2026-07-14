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

public class BookRepository implements AutoCloseable {

    private final Connection connection;

    public BookRepository(String dbPath) {
        try {
            connection = DriverManager.getConnection("jdbc:sqlite:" + dbPath);
            initSchema();
        } catch (SQLException e) {
            throw new RuntimeException("Failed to open SQLite database: " + dbPath, e);
        }
    }

    private void initSchema() {
        String sql = "CREATE TABLE IF NOT EXISTS books ("
                + "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                + "title TEXT NOT NULL,"
                + "author TEXT NOT NULL,"
                + "year INTEGER,"
                + "isbn TEXT"
                + ")";
        try (Statement stmt = connection.createStatement()) {
            stmt.execute(sql);
        } catch (SQLException e) {
            throw new RuntimeException("Failed to initialize schema", e);
        }
    }

    public Book create(Book book) {
        String sql = "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)";
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
                    book.setId(keys.getLong(1));
                }
            }
            return book;
        } catch (SQLException e) {
            throw new RuntimeException("Failed to create book", e);
        }
    }

    public List<Book> findAll(String authorFilter) {
        String sql;
        if (authorFilter != null && !authorFilter.isBlank()) {
            sql = "SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id";
        } else {
            sql = "SELECT id, title, author, year, isbn FROM books ORDER BY id";
        }
        List<Book> books = new ArrayList<>();
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            if (authorFilter != null && !authorFilter.isBlank()) {
                ps.setString(1, authorFilter);
            }
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    books.add(map(rs));
                }
            }
        } catch (SQLException e) {
            throw new RuntimeException("Failed to list books", e);
        }
        return books;
    }

    public Optional<Book> findById(long id) {
        String sql = "SELECT id, title, author, year, isbn FROM books WHERE id = ?";
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            ps.setLong(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                if (rs.next()) {
                    return Optional.of(map(rs));
                }
            }
        } catch (SQLException e) {
            throw new RuntimeException("Failed to find book", e);
        }
        return Optional.empty();
    }

    public boolean update(long id, Book book) {
        String sql = "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?";
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
            if (rows > 0) {
                book.setId(id);
            }
            return rows > 0;
        } catch (SQLException e) {
            throw new RuntimeException("Failed to update book", e);
        }
    }

    public boolean delete(long id) {
        String sql = "DELETE FROM books WHERE id = ?";
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            ps.setLong(1, id);
            return ps.executeUpdate() > 0;
        } catch (SQLException e) {
            throw new RuntimeException("Failed to delete book", e);
        }
    }

    private Book map(ResultSet rs) throws SQLException {
        Book book = new Book();
        book.setId(rs.getLong("id"));
        book.setTitle(rs.getString("title"));
        book.setAuthor(rs.getString("author"));
        int year = rs.getInt("year");
        if (rs.wasNull()) {
            book.setYear(null);
        } else {
            book.setYear(year);
        }
        book.setIsbn(rs.getString("isbn"));
        return book;
    }

    @Override
    public void close() {
        try {
            if (connection != null) {
                connection.close();
            }
        } catch (SQLException e) {
            // ignore
        }
    }
}
