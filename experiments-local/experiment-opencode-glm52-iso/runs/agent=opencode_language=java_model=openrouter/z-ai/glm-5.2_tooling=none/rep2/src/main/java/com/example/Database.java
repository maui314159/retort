package com.example;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;

public class Database implements AutoCloseable {

    private final Connection connection;

    public Database(String url) throws SQLException {
        connection = DriverManager.getConnection(url);
        initSchema();
    }

    public Database() throws SQLException {
        this("jdbc:sqlite::memory:");
    }

    private void initSchema() throws SQLException {
        try (Statement st = connection.createStatement()) {
            st.execute(
                "CREATE TABLE IF NOT EXISTS books ("
                + "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                + "title TEXT NOT NULL, "
                + "author TEXT NOT NULL, "
                + "year INTEGER, "
                + "isbn TEXT)");
        }
    }

    public Book insert(Book book) throws SQLException {
        String sql = "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)";
        try (PreparedStatement ps = connection.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS)) {
            ps.setString(1, book.getTitle());
            ps.setString(2, book.getAuthor());
            if (book.getYear() != null) ps.setInt(3, book.getYear()); else ps.setNull(3, java.sql.Types.INTEGER);
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

    public List<Book> findAll(String authorFilter) throws SQLException {
        StringBuilder sql = new StringBuilder("SELECT id, title, author, year, isbn FROM books");
        List<Object> params = new ArrayList<>();
        if (authorFilter != null && !authorFilter.isEmpty()) {
            sql.append(" WHERE author = ?");
            params.add(authorFilter);
        }
        sql.append(" ORDER BY id");
        try (PreparedStatement ps = connection.prepareStatement(sql.toString())) {
            for (int i = 0; i < params.size(); i++) {
                ps.setObject(i + 1, params.get(i));
            }
            return collect(ps.executeQuery());
        }
    }

    public Book findById(Long id) throws SQLException {
        try (PreparedStatement ps = connection.prepareStatement(
                "SELECT id, title, author, year, isbn FROM books WHERE id = ?")) {
            ps.setLong(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                if (rs.next()) return map(rs);
                return null;
            }
        }
    }

    public boolean update(Long id, Book book) throws SQLException {
        try (PreparedStatement ps = connection.prepareStatement(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?")) {
            ps.setString(1, book.getTitle());
            ps.setString(2, book.getAuthor());
            if (book.getYear() != null) ps.setInt(3, book.getYear()); else ps.setNull(3, java.sql.Types.INTEGER);
            ps.setString(4, book.getIsbn());
            ps.setLong(5, id);
            return ps.executeUpdate() > 0;
        }
    }

    public boolean delete(Long id) throws SQLException {
        try (PreparedStatement ps = connection.prepareStatement("DELETE FROM books WHERE id = ?")) {
            ps.setLong(1, id);
            return ps.executeUpdate() > 0;
        }
    }

    private List<Book> collect(ResultSet rs) throws SQLException {
        List<Book> books = new ArrayList<>();
        while (rs.next()) books.add(map(rs));
        return books;
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

    @Override
    public void close() throws SQLException {
        if (connection != null && !connection.isClosed()) {
            connection.close();
        }
    }
}
