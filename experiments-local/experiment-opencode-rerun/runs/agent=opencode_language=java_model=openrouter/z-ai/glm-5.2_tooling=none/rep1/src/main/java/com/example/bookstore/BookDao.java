package com.example.bookstore;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

public class BookDao {

    private final String url;
    private Connection connection;

    public BookDao(String url) {
        this.url = url;
    }

    public synchronized void init() throws SQLException {
        if (connection != null && !connection.isClosed()) {
            try (Statement st = connection.createStatement()) {
                st.execute(createTableSql());
            }
            return;
        }
        connection = DriverManager.getConnection(url);
        try (Statement st = connection.createStatement()) {
            st.execute(createTableSql());
        }
    }

    public synchronized Book create(Book book) throws SQLException {
        String sql = "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)";
        try (PreparedStatement ps = connection.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS)) {
            ps.setString(1, book.getTitle());
            ps.setString(2, book.getAuthor());
            if (book.getYear() != null) ps.setInt(3, book.getYear()); else ps.setNull(3, java.sql.Types.INTEGER);
            if (book.getIsbn() != null) ps.setString(4, book.getIsbn()); else ps.setNull(4, java.sql.Types.VARCHAR);
            ps.executeUpdate();
            try (ResultSet keys = ps.getGeneratedKeys()) {
                if (keys.next()) {
                    book.setId(keys.getLong(1));
                }
            }
        }
        return book;
    }

    public synchronized List<Book> list(String authorFilter) throws SQLException {
        StringBuilder sql = new StringBuilder("SELECT id, title, author, year, isbn FROM books");
        List<Object> params = new ArrayList<>();
        if (authorFilter != null && !authorFilter.trim().isEmpty()) {
            sql.append(" WHERE author = ?");
            params.add(authorFilter);
        }
        sql.append(" ORDER BY id ASC");
        try (PreparedStatement ps = connection.prepareStatement(sql.toString())) {
            for (int i = 0; i < params.size(); i++) {
                ps.setString(i + 1, (String) params.get(i));
            }
            try (ResultSet rs = ps.executeQuery()) {
                List<Book> out = new ArrayList<>();
                while (rs.next()) {
                    out.add(map(rs));
                }
                return out;
            }
        }
    }

    public synchronized Optional<Book> get(long id) throws SQLException {
        String sql = "SELECT id, title, author, year, isbn FROM books WHERE id = ?";
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            ps.setLong(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                if (rs.next()) return Optional.of(map(rs));
                return Optional.empty();
            }
        }
    }

    public synchronized boolean update(long id, Book book) throws SQLException {
        String sql = "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?";
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            ps.setString(1, book.getTitle());
            ps.setString(2, book.getAuthor());
            if (book.getYear() != null) ps.setInt(3, book.getYear()); else ps.setNull(3, java.sql.Types.INTEGER);
            if (book.getIsbn() != null) ps.setString(4, book.getIsbn()); else ps.setNull(4, java.sql.Types.VARCHAR);
            ps.setLong(5, id);
            return ps.executeUpdate() > 0;
        }
    }

    public synchronized boolean delete(long id) throws SQLException {
        String sql = "DELETE FROM books WHERE id = ?";
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            ps.setLong(1, id);
            return ps.executeUpdate() > 0;
        }
    }

    public synchronized void close() throws SQLException {
        if (connection != null && !connection.isClosed()) {
            connection.close();
        }
    }

    private Book map(ResultSet rs) throws SQLException {
        Book b = new Book();
        b.setId(rs.getLong("id"));
        b.setTitle(rs.getString("title"));
        b.setAuthor(rs.getString("author"));
        int year = rs.getInt("year");
        b.setYear(rs.wasNull() ? null : year);
        b.setIsbn(rs.getString("isbn"));
        return b;
    }

    private static String createTableSql() {
        return "CREATE TABLE IF NOT EXISTS books (" +
               "  id INTEGER PRIMARY KEY AUTOINCREMENT, " +
               "  title TEXT NOT NULL, " +
               "  author TEXT NOT NULL, " +
               "  year INTEGER, " +
               "  isbn TEXT" +
               ")";
    }
}
