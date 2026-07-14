package com.example.books;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;

public class BookRepository {

    private static final String CREATE_TABLE_SQL =
            "CREATE TABLE IF NOT EXISTS books ("
          + "id INTEGER PRIMARY KEY AUTOINCREMENT, "
          + "title TEXT NOT NULL, "
          + "author TEXT NOT NULL, "
          + "year INTEGER, "
          + "isbn TEXT)";

    private static final String INSERT_SQL =
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)";

    private static final String UPDATE_SQL =
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?";

    private final Connection connection;

    public BookRepository(String dbPath) throws SQLException {
        Connection conn = DriverManager.getConnection("jdbc:sqlite:" + dbPath);
        try (Statement st = conn.createStatement()) {
            st.execute(CREATE_TABLE_SQL);
        }
        this.connection = conn;
    }

    BookRepository(Connection connection) throws SQLException {
        try (Statement st = connection.createStatement()) {
            st.execute(CREATE_TABLE_SQL);
        }
        this.connection = connection;
    }

    public Book create(Book book) throws SQLException {
        try (PreparedStatement ps = connection.prepareStatement(INSERT_SQL,
                Statement.RETURN_GENERATED_KEYS)) {
            ps.setString(1, book.getTitle());
            ps.setString(2, book.getAuthor());
            if (book.getYear() != null) ps.setInt(3, book.getYear()); else ps.setNull(3, java.sql.Types.INTEGER);
            ps.setString(4, book.getIsbn());
            ps.executeUpdate();
            try (ResultSet keys = ps.getGeneratedKeys()) {
                if (keys.next()) book.setId(keys.getLong(1));
            }
            return book;
        }
    }

    public List<Book> findAll(String authorFilter) throws SQLException {
        String sql = "SELECT id, title, author, year, isbn FROM books";
        List<Book> books = new ArrayList<>();
        if (authorFilter != null && !authorFilter.isBlank()) {
            sql += " WHERE author = ?";
            try (PreparedStatement ps = connection.prepareStatement(sql)) {
                ps.setString(1, authorFilter);
                collect(ps.executeQuery(), books);
            }
        } else {
            try (Statement st = connection.createStatement();
                 ResultSet rs = st.executeQuery(sql)) {
                collect(rs, books);
            }
        }
        return books;
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
        try (PreparedStatement ps = connection.prepareStatement(UPDATE_SQL)) {
            ps.setString(1, book.getTitle());
            ps.setString(2, book.getAuthor());
            if (book.getYear() != null) ps.setInt(3, book.getYear()); else ps.setNull(3, java.sql.Types.INTEGER);
            ps.setString(4, book.getIsbn());
            ps.setLong(5, id);
            return ps.executeUpdate() > 0;
        }
    }

    public boolean delete(Long id) throws SQLException {
        try (PreparedStatement ps = connection.prepareStatement(
                "DELETE FROM books WHERE id = ?")) {
            ps.setLong(1, id);
            return ps.executeUpdate() > 0;
        }
    }

    private void collect(ResultSet rs, List<Book> books) throws SQLException {
        while (rs.next()) books.add(map(rs));
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

    public void close() throws SQLException {
        connection.close();
    }
}
